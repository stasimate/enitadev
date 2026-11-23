"""Practice use cases: make an exercise (multi-agent + MCP) and check an answer."""

import asyncio
import logging
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
from enita.agent.formats import correct_answer_text
from enita.agent.pipeline import AgentLike, GenerationError, generate_exercise
from enita.agent.prompts import VERIFIER_SYSTEM, WRITER_SYSTEM
from enita.audit import summarize_spans
from enita.content.loader import ContentRepository
from enita.guardrails.checks import validate_answer
from enita.models import (
    CLOSED_TYPES,
    MAX_ATTEMPTS,
    WRITING_TYPES,
    AttemptFeedback,
    Exercise,
    ExerciseDraft,
    ExerciseType,
    Grade,
    LearnerProfile,
    Solution,
    Verification,
)
from enita.practice.checker import check_answer
from enita.practice.tutor import (
    GENERIC_HINT,
    default_grader,
    default_memory_agent,
    grade_answer,
    mask_solution,
    rewrite_memory,
)
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


class ExerciseClosed(RuntimeError):
    """The exercise is done (correct, max attempts or solution shown)."""


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
            "ENITA_EMBEDDING_MODEL": settings.embedding_model,
            "ENITA_QDRANT_URL": settings.qdrant_url or "",
            "OPENAI_API_KEY": (
                settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
            ),
        }
        async with MCPClient(
            command=sys.executable,
            args=["-m", "enita.mcp_server"],
            env=env,
            timeout=settings.mcp_timeout_s,
        ) as c:
            yield await c.a_list_tools()

    return provider


WRITER_TOOLS = {"get_theory_card", "get_learner_profile"}
EXPLAINER_TOOLS = {"search_grammar", "get_learner_profile"}


def only(tools: list[Any], names: set[str]) -> list[Any]:
    """Least privilege: give an agent only the MCP tools that its job needs."""
    return [t for t in tools if t.name in names]


def default_agents(settings: Settings) -> AgentsFactory:
    def factory(tools: list[Any]) -> tuple[AgentLike, AgentLike]:
        writer = Agent(
            name="writer",
            client=get_client(settings, settings.writer_model),
            system_prompt=WRITER_SYSTEM,
            tools=only(tools, WRITER_TOOLS),
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


def pick_type(level: str) -> ExerciseType:
    """Writing is the core: 80% writing types (50% at A1), the rest are closed warm-ups."""
    writing_share = 0.5 if level == "A1" else 0.8
    pool = WRITING_TYPES if random.random() < writing_share else CLOSED_TYPES
    return random.choice(pool)


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
        grader: Callable[[], Any] | None = None,
        memory_agent: Callable[[], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.content = content
        self.db = db
        self.tools = tools or mcp_tools(settings)
        self.agents = agents or default_agents(settings)
        self.grader = grader or (lambda: default_grader(settings))
        self.memory_agent = memory_agent or (lambda: default_memory_agent(settings))
        self._tasks: set[asyncio.Task[None]] = set()
        self._refilling: set[str] = set()
        self._jobs: dict[str, asyncio.Task[None]] = {}

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

    def _schedule(self, key: str, coro: Any) -> None:
        """Run a background job. A second job with the same key waits for the first."""
        previous = self._jobs.get(key)

        async def run() -> None:
            if previous is not None:
                await asyncio.gather(previous, return_exceptions=True)
            await coro

        task = asyncio.create_task(run())
        self._jobs[key] = task
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

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
        kind: ExerciseType = exercise_type or pick_type(card.level)
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
                            recent_prompts=self.db.recent_prompts(topic_id),
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

    async def answer(self, exercise_id: str, answer: str) -> AttemptFeedback:
        """Check one attempt. A wrong attempt leaves the exercise open for a new attempt."""
        item = self.db.get_exercise(exercise_id)
        if item is None:
            raise ExerciseNotFound(exercise_id)
        if self.db.is_closed(exercise_id):
            raise ExerciseClosed(exercise_id)
        history = self.db.attempts_of(exercise_id)
        number = len(history) + 1
        draft, topic_id = item.draft, item.topic_id
        rule_ref = f"{topic_id}#{draft.rule_section}"

        guard = validate_answer(answer)
        notes: list[str] = []
        corrected: str | None = None
        if guard.flagged:
            verdict, score, feedback, hint = "wrong", 0.0, FLAGGED_EXPLANATION, GENERIC_HINT
            self.db.add_audit(
                "guardrail.input",
                "flagged",
                {"exercise_id": item.id, "reasons": guard.reasons},
                topic_id,
            )
        elif draft.type in WRITING_TYPES:
            grade = await self._grade(item, guard.text, history)
            verdict, score, feedback = grade.verdict, grade.score, grade.feedback
            hint, notes, corrected = grade.hint or None, grade.errors, grade.corrected
            rule_ref = f"{topic_id}#{grade.rule_section}"
        else:
            closed = check_answer(draft, topic_id, guard.text)
            verdict, score = closed.verdict, closed.score
            if verdict == "correct":
                feedback, hint = closed.explanation, None
            else:
                feedback = "Non è ancora corretto."
                hint = f"Rileggi la sezione «{draft.rule_section.capitalize()}» della scheda."
                notes = [f"errore su {draft.rule_section}"]

        done = verdict == "correct" or number >= MAX_ATTEMPTS
        if not done:
            # The next attempt must not see the solution in the feedback, hint or notes.
            feedback = mask_solution(feedback, guard.text, draft.answers)
            hint = mask_solution(hint, guard.text, draft.answers) if hint else hint
            shown_notes = [mask_solution(n, guard.text, draft.answers) for n in notes]
        else:
            shown_notes = notes
        self.db.add_attempt(
            item,
            guard.text,
            verdict=verdict,
            score=score,
            rule_ref=rule_ref,
            flagged=guard.flagged,
            notes=notes,
            corrected=corrected,
        )
        self.db.add_audit(
            "answer.check",
            verdict,
            {
                "exercise_id": item.id,
                "attempt": number,
                "flagged": guard.flagged,
                "rule_ref": rule_ref,
                "notes": notes,
            },
            topic_id,
        )
        solution = None
        if done:
            solution = self._close(item, corrected if verdict != "correct" else None)
        return AttemptFeedback(
            attempt=number,
            verdict=verdict,
            score=score,
            feedback=feedback,
            hint=None if done else hint,
            errors=shown_notes,
            rule_ref=rule_ref,
            done=done,
            solution=solution,
        )

    def solution(self, exercise_id: str) -> Solution:
        """Show the solution: the model answer and the student's last text, corrected."""
        item = self.db.get_exercise(exercise_id)
        if item is None:
            raise ExerciseNotFound(exercise_id)
        attempts = self.db.attempts_of(exercise_id)
        last = next((a["corrected"] for a in reversed(attempts) if a["corrected"]), None)
        if self.db.is_closed(exercise_id):
            return self._solution(item, last)
        self.db.add_audit("exercise.solution", "shown", {"exercise_id": item.id}, item.topic_id)
        return self._close(item, last)

    def _solution(self, item: StoredExercise, corrected: str | None) -> Solution:
        return Solution(
            model_answer=correct_answer_text(item.draft),
            corrected=corrected,
            explanation=item.draft.explanation,
        )

    def _close(self, item: StoredExercise, corrected: str | None) -> Solution:
        """Close the exercise and start the memory rewrite of its topic."""
        self.db.close_exercise(item.id)
        self._schedule(f"memory:{item.topic_id}", self._update_memory(item.topic_id))
        return self._solution(item, corrected)

    async def _grade(self, item: StoredExercise, answer: str, history: list[dict]) -> Grade:
        card = self.content.get(item.topic_id)
        record: dict[str, Any] = {"exercise_id": item.id}
        outcome = "error"
        try:
            with ContextTracing().trace("answer.grade") as trace:
                try:
                    async with asyncio.timeout(self.settings.grade_timeout_s):
                        grade = await grade_answer(self.grader(), card, item.draft, answer, history)
                finally:
                    record.update(summarize_spans(trace.get_spans()))
            outcome = grade.verdict
            return grade
        except BaseException as exc:
            cause = _root_cause(exc)
            record["error"] = f"{type(cause).__name__}: {cause}"[:500]
            if isinstance(cause, TimeoutError):
                outcome = "timeout"
                raise GenerationTimeout(record["error"]) from exc
            if isinstance(cause, GenerationError | ProviderConfigError):
                raise cause from exc
            if isinstance(cause, Exception):
                raise ProviderCallError(record["error"]) from exc
            raise
        finally:
            self.db.add_audit("answer.grade", outcome, record, item.topic_id)

    async def _update_memory(self, topic_id: str) -> None:
        """Rewrite the topic memory, then replace the prepared exercises (they are old)."""
        card = self.content.get(topic_id)
        try:
            with ContextTracing().trace("memory.rewrite") as trace:
                async with asyncio.timeout(self.settings.grade_timeout_s):
                    memory = await rewrite_memory(
                        self.memory_agent(),
                        card,
                        self.db.get_memory(topic_id),
                        self.db.finished_exercises(topic_id),
                    )
                record = summarize_spans(trace.get_spans())
            self.db.set_memory(topic_id, memory)
            record["memory"] = memory.model_dump()
            record["pool_cleared"] = self.db.clear_pool(topic_id)
            self.db.add_audit("memory.rewrite", "updated", record, topic_id)
            self._schedule_refill(topic_id)
        except Exception as exc:  # noqa: BLE001 - a background failure must not stop the app
            log.warning("Memory rewrite for %s failed: %s", topic_id, exc)
            self.db.add_audit("memory.rewrite", "error", {"error": str(exc)[:300]}, topic_id)

    def profile(self, topic_id: str | None = None) -> LearnerProfile:
        return self.db.profile(topic_id)
