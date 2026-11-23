"""Load and parse the theory cards in `content/en/topics/*.md`."""

import re
from pathlib import Path

import yaml

from enita.models import SECTION_SLUGS, Level, Section, TopicCard, TopicSummary

_FRONT_MATTER = re.compile(r"\A---\n(?P<meta>.*?)\n---\n(?P<body>.*)\Z", re.DOTALL)
_H2 = re.compile(r"^## +(?P<title>.+?)\s*$", re.MULTILINE)
_LEVEL_ORDER: dict[Level, int] = {"A1": 0, "A2": 1, "B1": 2, "B2": 3}


class ContentError(ValueError):
    """A theory card does not obey the content rules in AGENTS.md."""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_card(text: str, source: str = "<string>") -> TopicCard:
    match = _FRONT_MATTER.match(text)
    if not match:
        raise ContentError(f"{source}: the YAML front matter is missing")
    meta = yaml.safe_load(match["meta"]) or {}
    body = match["body"]

    headings = list(_H2.finditer(body))
    sections: list[Section] = []
    for i, h in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        sections.append(
            Section(
                slug=slugify(h["title"]),
                title=h["title"],
                markdown=body[h.end() : end].strip(),
            )
        )

    slugs = tuple(s.slug for s in sections)
    if slugs != SECTION_SLUGS:
        raise ContentError(f"{source}: the sections must be {SECTION_SLUGS}, found {slugs}")

    try:
        return TopicCard(**meta, sections=sections)
    except Exception as exc:  # pydantic.ValidationError and TypeError
        raise ContentError(f"{source}: the front matter is not valid: {exc}") from exc


class ContentRepository:
    """Read-only access to the theory cards. The cards load one time, on the first use."""

    def __init__(self, content_dir: Path) -> None:
        self._dir = content_dir
        self._cards: dict[str, TopicCard] | None = None

    def _load(self) -> dict[str, TopicCard]:
        if self._cards is None:
            cards: dict[str, TopicCard] = {}
            for path in sorted(self._dir.glob("*.md")):
                card = parse_card(path.read_text(encoding="utf-8"), source=path.name)
                if card.id != path.stem:
                    raise ContentError(f"{path.name}: the id '{card.id}' is not the filename")
                cards[card.id] = card
            self._cards = cards
        return self._cards

    def list_topics(self) -> list[TopicSummary]:
        cards = sorted(self._load().values(), key=lambda c: (_LEVEL_ORDER[c.level], c.title))
        return [TopicSummary(**c.model_dump(exclude={"sections"})) for c in cards]

    def get(self, topic_id: str) -> TopicCard | None:
        return self._load().get(topic_id)

    def rule_ref_exists(self, rule_ref: str) -> bool:
        topic_id, _, slug = rule_ref.partition("#")
        card = self.get(topic_id)
        return card is not None and card.has_section(slug)
