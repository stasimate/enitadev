"""Practice use cases: make an exercise (multi-agent + MCP) and check an answer."""

import os
import random
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from datapizza.agents import Agent
from datapizza.tools.mcp_client import MCPClient
from datapizza.tracing import ContextTracing

from enita.agent.clients import ProviderConfigError, get_client
from enita.agent.pipeline import AgentLike, GenerationError, generate_exercise
from enita.agent.prompts import VERIFIER_SYSTEM, WRITER_SYSTEM
from enita.audit import summarize_spans
from enita.content.loader import ContentRepository
from enita.guardrails.checks import validate_answer
from enita.models import (
    Exercise,
    ExerciseDraft,
    ExerciseType,
    Feedback,
    LearnerProfile,
    Verification,
)
from enita.practice.checker import check_answer
from enita.settings import Settings
from enita.storage.db import Database

ToolsProvider = Callable[[], AbstractAsyncContextManager[list[Any]]]
AgentsFactory = Callable[[list[Any]], tuple[AgentLike, AgentLike]]


class TopicNotFound(LookupError):
    pass


class ExerciseNotFound(LookupError):
    pass


class ProviderCallError(RuntimeError):
    """The LLM provider refused or failed the request (for example, a wrong API key)."""


def _root_cause(exc: BaseException) -> BaseException:
    while isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc


def mcp_tools(settings: Settings) -> ToolsProvider:
    """Start the Enita MCP server (stdio) and give its tools to the agents."""

    @asynccontextmanager
    async def provider() -> AsyncIterator[list[Any]]:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "ENITA_CONTENT_DIR": str(settings.content_dir),
            "ENITA_DB_PATH": str(settings.db_path),
        }
        async with MCPClient(command=sys.executable, args=["-m", "enita.mcp_server"], env=env) as c:
            yield await c.a_list_tools()

    return provider


def default_agents(settings: Settings) -> AgentsFactory:
    def factory(tools: list[Any]) -> tuple[AgentLike, AgentLike]:
        writer = Agent(
            name="writer",
            client=get_client(settings, settings.writer_model),
            system_prompt=WRITER_SYSTEM,
            tools=tools,
            output_cls=ExerciseDraft,
            max_steps=4,
        )
        verifier = Agent(
            name="verifier",
            client=get_client(settings, settings.verifier_model),
            system_prompt=VERIFIER_SYSTEM,
            output_cls=Verification,
            max_steps=1,
        )
        return writer, verifier

    return factory


FLAGGED_EXPLANATION = (
    "La risposta contiene istruzioni rivolte al sistema, quindi non viene valutata. "
    "Scrivi solo la parola o la frase richiesta."
)


class PracticeService:
    def __init__(
        self,
        settings: Settings,
        content: ContentRepository,
        db: Database,
        tools: ToolsProvider | None = None,
        agents: AgentsFactory | None = None,
    ) -> None:
        self.settings = settings
        self.content = content
        self.db = db
        self.tools = tools or mcp_tools(settings)
        self.agents = agents or default_agents(settings)

    async def create(self, topic_id: str, exercise_type: ExerciseType | None) -> Exercise:
        card = self.content.get(topic_id)
        if card is None:
            raise TopicNotFound(topic_id)
        kind: ExerciseType = exercise_type or random.choice(["fill_blank", "multiple_choice"])
        record: dict[str, Any] = {"exercise_type": kind}
        outcome = "error"

        try:
            # Audit trail (RNF-04): the trace records the LLM calls, the tool calls and tokens.
            with ContextTracing().trace("exercise.generate") as trace:
                try:
                    async with self.tools() as tools:
                        writer, verifier = self.agents(tools)
                        result = await generate_exercise(
                            writer,
                            verifier,
                            topic_id=topic_id,
                            exercise_type=kind,
                            card=card.as_markdown(),
                            max_attempts=self.settings.max_writer_attempts,
                        )
                finally:
                    record.update(summarize_spans(trace.get_spans()))
            outcome = "approved"
            record.update(attempts=result.attempts, rejected=result.rejected)
        except BaseException as exc:
            # The MCP stdio client wraps errors in exception groups. Get the root cause.
            cause = _root_cause(exc)
            record["error"] = f"{type(cause).__name__}: {cause}"[:500]
            if isinstance(cause, GenerationError):
                outcome = "rejected"
            if isinstance(cause, GenerationError | ProviderConfigError):
                raise cause from exc
            if isinstance(cause, Exception):
                raise ProviderCallError(record["error"]) from exc
            raise
        finally:
            self.db.add_audit("exercise.generate", outcome, record, topic_id)

        item = self.db.add_exercise(topic_id, result.draft)
        return item.public()

    def answer(self, exercise_id: str, answer: str) -> Feedback:
        item = self.db.get_exercise(exercise_id)
        if item is None:
            raise ExerciseNotFound(exercise_id)

        guard = validate_answer(answer)
        if guard.flagged:
            feedback = Feedback(
                verdict="wrong",
                score=0.0,
                correct_answer=item.draft.answers[0],
                explanation=FLAGGED_EXPLANATION,
                rule_ref=f"{item.topic_id}#{item.draft.rule_section}",
            )
            self.db.add_audit(
                "guardrail.input",
                "flagged",
                {"exercise_id": item.id, "reasons": guard.reasons},
                item.topic_id,
            )
        else:
            feedback = check_answer(item.draft, item.topic_id, guard.text)

        self.db.add_attempt(item, guard.text, feedback, flagged=guard.flagged)
        self.db.add_audit(
            "answer.check",
            feedback.verdict,
            {"exercise_id": item.id, "flagged": guard.flagged, "rule_ref": feedback.rule_ref},
            item.topic_id,
        )
        return feedback

    def profile(self, topic_id: str | None = None) -> LearnerProfile:
        return self.db.profile(topic_id)
