"""Hybrid search on the theory cards: dense embeddings (Qdrant) + BM25, fused with RRF.

One chunk = one section of a card, so each result has a `rule_ref` (`topic#section`).
The embeddings are cached on disk by content hash: an unchanged card is never embedded
again. Without ENITA_QDRANT_URL, Qdrant runs in memory inside the process.
"""

import hashlib
import json
import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from datapizza.core.vectorstore import Distance, VectorConfig
from datapizza.type import Chunk, DenseEmbedding
from datapizza.vectorstores.qdrant import QdrantVectorstore

from enita.content.loader import ContentRepository
from enita.settings import Settings

VECTOR = "embedding"
RRF_K = 60
MIN_TOPIC_PASSAGES = 2
_TOKEN = re.compile(r"[a-zà-ù']+")


class RagUnavailable(RuntimeError):
    """The RAG index cannot operate (for example, no OpenAI key for the embeddings)."""


@dataclass(frozen=True)
class Passage:
    rule_ref: str
    title: str
    text: str


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def build_passages(content: ContentRepository) -> list[Passage]:
    passages = []
    for summary in content.list_topics():
        card = content.get(summary.id)
        for section in card.sections:
            passages.append(
                Passage(
                    rule_ref=f"{card.id}#{section.slug}",
                    title=f"{card.title} · {section.title}",
                    text=f"{card.title} ({card.level}) · {section.title}\n{section.markdown}",
                )
            )
    return passages


class Bm25:
    """A small BM25 (k1=1.5, b=0.75). The corpus has some tens of passages."""

    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = [Counter(_tokens(d)) for d in docs]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(len(self.docs), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: str) -> list[float]:
        q = _tokens(query)
        out = []
        for doc, length in zip(self.docs, self.lengths, strict=True):
            s = 0.0
            for t in q:
                if t in doc:
                    tf = doc[t]
                    norm = tf + self.k1 * (1 - self.b + self.b * length / self.avg)
                    s += self.idf[t] * tf * (self.k1 + 1) / norm
            out.append(s)
        return out


class EmbeddingCache:
    def __init__(self, path: Path, model: str) -> None:
        self.path, self.model = path, model
        try:
            self.data: dict[str, list[float]] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def key(self, text: str) -> str:
        return hashlib.sha256(f"{self.model}\n{text}".encode()).hexdigest()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data), encoding="utf-8")


class GrammarIndex:
    def __init__(self, settings: Settings, content: ContentRepository) -> None:
        if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
            raise RagUnavailable("OPENAI_API_KEY is necessary for the embeddings of the RAG.")
        from datapizza.embedders.openai import OpenAIEmbedder

        self.settings = settings
        self.embedder = OpenAIEmbedder(
            api_key=settings.openai_api_key.get_secret_value(),
            model_name=settings.embedding_model,
        )
        self.passages = build_passages(content)
        self.by_ref = {p.rule_ref: p for p in self.passages}
        self.bm25 = Bm25([p.text for p in self.passages])
        digest = hashlib.sha256(
            "\n".join([settings.embedding_model, *(p.text for p in self.passages)]).encode()
        ).hexdigest()
        self.collection = f"enita_grammar_{digest[:10]}"
        self.cache = EmbeddingCache(
            settings.db_path.parent / "embeddings.json", settings.embedding_model
        )
        self.store = (
            QdrantVectorstore(location=settings.qdrant_url)
            if settings.qdrant_url
            else QdrantVectorstore(location=":memory:")
        )
        self._ensure_collection()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        missing = [t for t in texts if self.cache.key(t) not in self.cache.data]
        if missing:
            vectors = self.embedder.embed(missing)
            for text, vector in zip(missing, vectors, strict=True):
                self.cache.data[self.cache.key(text)] = vector
            self.cache.save()
        return [self.cache.data[self.cache.key(t)] for t in texts]

    def _ensure_collection(self) -> None:
        existing = {c.name for c in self.store.get_collections().collections}
        if self.collection in existing:
            return
        vectors = self._embed([p.text for p in self.passages])
        self.store.create_collection(
            self.collection,
            vector_config=[
                VectorConfig(name=VECTOR, dimensions=len(vectors[0]), distance=Distance.COSINE)
            ],
        )
        chunks = [
            Chunk(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, p.rule_ref)),
                text=p.text,
                embeddings=[DenseEmbedding(name=VECTOR, vector=v)],
                metadata={"rule_ref": p.rule_ref, "title": p.title},
            )
            for p, v in zip(self.passages, vectors, strict=True)
        ]
        self.store.add(chunks, self.collection)

    def search(
        self, query: str, k: int | None = None, topic_id: str | None = None
    ) -> list[Passage]:
        """Hybrid search. With topic_id, passages of that topic get a small boost."""
        k = k or self.settings.rag_top_k
        n = len(self.passages)
        dense = self.store.search(self.collection, self._embed([query])[0], k=min(10, n))
        dense_rank = [c.metadata["rule_ref"] for c in dense]
        bm = self.bm25.scores(query)
        lexical_rank = [
            self.passages[i].rule_ref for i in sorted(range(n), key=lambda i: -bm[i]) if bm[i] > 0
        ][:10]

        fused: dict[str, float] = {}
        for ranking in (dense_rank, lexical_rank):
            for pos, ref in enumerate(ranking):
                fused[ref] = fused.get(ref, 0.0) + 1 / (RRF_K + pos + 1)
        best = sorted(fused, key=lambda r: -fused[r])
        if topic_id:
            mine = [r for r in self.by_ref if r.startswith(f"{topic_id}#")]
            # Topic passages first (in fused order, then card order), then the others.
            ranked_mine = [r for r in best if r in mine] + [r for r in mine if r not in best]
            others = [r for r in best if r not in mine]
            # k - 1 topic passages and one other passage (useful for a comparison).
            take = max(MIN_TOPIC_PASSAGES, k - 1)
            best = ranked_mine[:take] + others
        return [self.by_ref[r] for r in best[:k]]
