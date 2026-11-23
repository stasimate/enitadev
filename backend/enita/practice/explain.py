"""Use case "Spiegami meglio": an agent explains the rule again with RAG on the cards."""

import asyncio
import re
from typing import Any

from datapizza.agents import Agent
from datapizza.tracing import ContextTracing

from enita.agent.clients import ProviderConfigError, get_client
from enita.agent.pipeline import GenerationError, _structured
from enita.agent.prompts import EXPLAINER_SYSTEM, EXPLAINER_TASK
from enita.audit import summarize_spans
from enita.content.loader import ContentRepository
from enita.guardrails.checks import injection_reasons
from enita.models import ExplainResponse, Explanation, Source
from enita.practice.service import (
    EXPLAINER_TOOLS,
    GenerationTimeout,
    ProviderCallError,
    ToolsProvider,
    TopicNotFound,
    _root_cause,
    mcp_tools,
    only,
)
from enita.settings import Settings
from enita.storage.db import Database

_REF_IN_TOOL_RESULT = re.compile(r'rule_ref\\*"\s*:\s*\\*"([a-z0-9-]+#[a-z]+)')


def retrieved_refs(spans: list[Any]) -> set[str]:
    """The rule_refs that search_grammar returned in this trace (the RAG context)."""
    refs: set[str] = set()
    for span in spans:
        if span.name.endswith("search_grammar"):
            refs |= set(
                _REF_IN_TOOL_RESULT.findall(str((span.attributes or {}).get("tool_result", "")))
            )
    return refs


def grounded_sources(
    out: Explanation, retrieved: set[str], content: ContentRepository
) -> list[str]:
    """Output guardrail: keep only sources that the agent retrieved and that exist."""
    return [s for s in dict.fromkeys(out.sources) if s in retrieved and content.rule_ref_exists(s)]


class ExplainService:
    def __init__(
        self,
        settings: Settings,
        content: ContentRepository,
        db: Database,
        tools: ToolsProvider | None = None,
        agent_factory: Any = None,
    ) -> None:
        self.settings, self.content, self.db = settings, content, db
        self.tools = tools or mcp_tools(settings)
        self.agent_factory = agent_factory or (
            lambda tools: Agent(
                name="explainer",
                client=get_client(settings),
                system_prompt=EXPLAINER_SYSTEM,
                tools=only(tools, EXPLAINER_TOOLS),
                output_cls=Explanation,
                max_steps=4,
            )
        )

    async def explain(self, topic_id: str) -> ExplainResponse:
        if self.content.get(topic_id) is None:
            raise TopicNotFound(topic_id)
        record: dict[str, Any] = {}
        outcome = "error"
        try:
            with ContextTracing().trace("topic.explain") as trace:
                try:
                    async with (
                        asyncio.timeout(self.settings.explain_timeout_s),
                        self.tools() as tools,
                    ):
                        agent = self.agent_factory(tools)
                        step = await agent.a_run(
                            EXPLAINER_TASK.format(topic_id=topic_id), tool_choice="required_first"
                        )
                        out = _structured(step, Explanation)
                finally:
                    spans = trace.get_spans()
                    record.update(summarize_spans(spans))
                    retrieved = retrieved_refs(spans)
            record["retrieved"] = sorted(retrieved)
            sources = grounded_sources(out, retrieved, self.content)
            record["sources"] = sources
            if not sources:
                outcome = "ungrounded"
                raise GenerationError("The explanation cites no retrieved passage.")
            if injection_reasons(out.explanation) or "<" in out.explanation:
                outcome = "rejected"
                raise GenerationError("The explanation contains HTML or AI instructions.")
            outcome = "approved"
        except BaseException as exc:
            cause = _root_cause(exc)
            record.setdefault("error", f"{type(cause).__name__}: {cause}"[:500])
            if isinstance(cause, TimeoutError):
                outcome = "timeout"
                raise GenerationTimeout(record["error"]) from exc
            if isinstance(cause, GenerationError | ProviderConfigError):
                raise cause from exc
            if isinstance(cause, Exception):
                raise ProviderCallError(record["error"]) from exc
            raise
        finally:
            self.db.add_audit("topic.explain", outcome, record, topic_id)

        titles = {s: self._title(s) for s in sources}
        return ExplainResponse(
            explanation=out.explanation,
            sources=[Source(rule_ref=s, title=titles[s]) for s in sources],
        )

    def _title(self, rule_ref: str) -> str:
        topic_id, _, slug = rule_ref.partition("#")
        card = self.content.get(topic_id)
        section = next(s for s in card.sections if s.slug == slug)
        return f"{card.title} · {section.title}"
