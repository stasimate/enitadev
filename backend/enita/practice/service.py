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
from enita.content.loader import ContentRepository
from enita.models import Exercise, ExerciseDraft, ExerciseType, Feedback, Verification
from enita.practice.checker import check_answer
from enita.settings import Settings
from enita.storage.exercises import ExerciseStore

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
        env = {"PATH": os.environ.get("PATH", ""), "ENITA_CONTENT_DIR": str(settings.content_dir)}
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


class PracticeService:
    def __init__(
        self,
        settings: Settings,
        content: ContentRepository,
        store: ExerciseStore,
        tools: ToolsProvider | None = None,
        agents: AgentsFactory | None = None,
    ) -> None:
        self.settings = settings
        self.content = content
        self.store = store
        self.tools = tools or mcp_tools(settings)
        self.agents = agents or default_agents(settings)

    async def create(self, topic_id: str, exercise_type: ExerciseType | None) -> Exercise:
        card = self.content.get(topic_id)
        if card is None:
            raise TopicNotFound(topic_id)
        kind: ExerciseType = exercise_type or random.choice(["fill_blank", "multiple_choice"])

        try:
            # Audit trail (RNF-04): the trace records the LLM calls, the tool calls and tokens.
            with ContextTracing().trace("exercise.generate"):
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
        except BaseException as exc:
            # The MCP stdio client wraps errors in exception groups. Get the root cause.
            cause = _root_cause(exc)
            if isinstance(cause, GenerationError | ProviderConfigError):
                raise cause from exc
            if isinstance(cause, Exception):
                raise ProviderCallError(f"{type(cause).__name__}: {cause}") from exc
            raise
        return self.store.add(topic_id, result.draft).public()

    def answer(self, exercise_id: str, answer: str) -> Feedback:
        item = self.store.get(exercise_id)
        if item is None:
            raise ExerciseNotFound(exercise_id)
        return check_answer(item.draft, item.topic_id, answer)
