"""Test doubles for the agents. They return fixed structured outputs."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from enita.models import ExerciseDraft, Verification

FILL = ExerciseDraft(
    type="fill_blank",
    instruction="Completa con la forma corretta del verbo 'work'.",
    prompt="She ___ in a bank.",
    options=[],
    answers=["works"],
    rule_section="regola",
    explanation="Alla terza persona singolare si aggiunge -s.",
)

CHOICE = ExerciseDraft(
    type="multiple_choice",
    instruction="Scegli la forma corretta.",
    prompt="___ she work on Sundays?",
    options=["Do", "Does", "Is"],
    answers=["Does"],
    rule_section="attenzione",
    explanation="Con he/she/it la domanda usa does.",
)


@dataclass
class Step:
    structured_data: list[BaseModel]
    text: str = ""


@dataclass
class FakeAgent:
    """Returns the outputs in sequence. It records each task input."""

    outputs: list[BaseModel]
    tasks: list[str] = field(default_factory=list)

    async def a_run(self, task_input: str, **kwargs: Any) -> Step:
        self.tasks.append(task_input)
        out = self.outputs[min(len(self.tasks), len(self.outputs)) - 1]
        return Step(structured_data=[out])


APPROVE = Verification(approved=True, issues=[])
REJECT = Verification(approved=False, issues=["Two answers are correct."])


@asynccontextmanager
async def no_tools() -> AsyncIterator[list[Any]]:
    yield []
