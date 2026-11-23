"""Practice use cases: make an exercise (multi-agent + MCP) and check an answer."""

import asyncio
import logging
import os
import random
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, get_args

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
from enita.storage.exercises import StoredExercise

log = logging.getLogger(__name__)

ToolsProvider = Callable[[], AbstractAsyncContextManager[list[Any]]]
AgentsFactory = Callable[[list[Any]], tuple[AgentLike, AgentLike]]


class TopicNotFound(LookupError):
    pass


class ExerciseNotFound(LookupError):
    pass


class GenerationTimeout(TimeoutError):
    """The generation took more time than ENITA_GENERATION_TIMEOUT_S."""


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
        async with MCPClient(
            command=sys.executable,
            args=["-m", "enita.mcp_server"],
            env=env,
            timeout=settings.mcp_timeout_s,
        ) as c:
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
        self._tasks: set[asyncio.Task[None]] = set()
        self._refilling: set[str] = set()

    async def create(self, topic_id: str, exercise_type: ExerciseType | None) -> Exercise:
        """Serve an exercise from the pool if one is ready, else generate it now."""
        if self.content.get(topic_id) is None:
            raise TopicNotFound(topic_id)
        item = self.db.take_pooled(topic_id, exercise_type)
        if item is not None:
            self.db.add_audit("exercise.serve", "pool", {"exercise_id": item.id}, topic_id)
        else:
            item = await self._generate(topic_id, exercise_type, served=True)
        self._schedule_refill(topic_id)
        return item.public()

    def prefetch(self, topic_id: str) -> None:
        """Start to fill the pool of a topic in the background."""
        if self.content.get(topic_id) is None:
            raise TopicNotFound(topic_id)
        self._schedule_refill(topic_id)

    async def wait_idle(self) -> None:
        """Wait for the background generations (for evals and tests)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    def _schedule_refill(self, topic_id: str) -> None:
        if self.settings.pool_size <= 0 or topic_id in self._refilling:
            return
        self._refilling.add(topic_id)
        task = asyncio.create_task(self._refill(topic_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _refill(self, topic_id: str) -> None:
        try:
            while self.db.count_pooled(topic_id) < self.settings.pool_size:
                await self._generate(topic_id, None, served=False)
        except Exception as exc:  # noqa: BLE001 - a background failure must not stop the app
            log.warning("Background generation for %s failed: %s", topic_id, exc)
        finally:
            self._refilling.discard(topic_id)

    async def _generate(
        self, topic_id: str, exercise_type: ExerciseType | None, *, served: bool
    ) -> StoredExercise:
        card = self.content.get(topic_id)
        if card is None:
            raise TopicNotFound(topic_id)
        kind: ExerciseType = exercise_type or random.choice(get_args(ExerciseType))
        record: dict[str, Any] = {"exercise_type": kind, "background": not served}
        outcome = "error"

        try:
            # Audit trail (RNF-04): the trace records the LLM calls, the tool calls and tokens.
            with ContextTracing().trace("exercise.generate") as trace:
                try:
                    async with (
                        asyncio.timeout(self.settings.generation_timeout_s),
                        self.tools() as tools,
                    ):
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
            if isinstance(cause, TimeoutError):
                outcome = "timeout"
                raise GenerationTimeout(record["error"]) from exc
            if isinstance(cause, GenerationError):
                outcome = "rejected"
            if isinstance(cause, GenerationError | ProviderConfigError):
                raise cause from exc
            if isinstance(cause, Exception):
                raise ProviderCallError(record["error"]) from exc
            raise
        finally:
            self.db.add_audit("exercise.generate", outcome, record, topic_id)

        return self.db.add_exercise(topic_id, result.draft, served=served)

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
