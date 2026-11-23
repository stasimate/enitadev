"""Test doubles for the agents. They return fixed structured outputs."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from enita.models import ExerciseDraft, Grade, TopicMemory, Verification

FILL = ExerciseDraft(
    type="fill_blank",
    instruction="Completa con la forma corretta del verbo 'work'.",
    prompt="She ___ in a bank.",
    options=[],
    answers=["works"],
    correction="",
    context="",
    criteria=[],
    rule_section="regola",
    explanation="Alla terza persona singolare si aggiunge -s.",
)

CHOICE = ExerciseDraft(
    type="multiple_choice",
    instruction="Scegli la forma corretta.",
    prompt="___ she work on Sundays?",
    options=["Do", "Does", "Is"],
    answers=["Does"],
    correction="",
    context="",
    criteria=[],
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


APPROVE = Verification(correct_options=["Does"], approved=True, issues=[])
REJECT = Verification(correct_options=[], approved=False, issues=["Two answers are correct."])


@asynccontextmanager
async def no_tools() -> AsyncIterator[list[Any]]:
    yield []


WRITE = ExerciseDraft(
    type="translate",
    instruction="Traduci in inglese.",
    prompt="Ieri Luca è andato al mercato.",
    options=[],
    answers=["Yesterday Luca went to the market."],
    correction="",
    context="Luca è appena arrivato a Londra.",
    criteria=["past simple irregolare: went", "traduzione fedele"],
    rule_section="regola",
    explanation="Go è irregolare: went.",
)

GRADE_WRONG = Grade(
    task_done=True,
    rule_correct=False,
    important_errors=0,
    verdict="wrong",
    score=0.2,
    feedback="Buona struttura, ma il verbo non è giusto.",
    hint="Go è un verbo irregolare.",
    errors=["past simple di go: went, non goed"],
    corrected="Yesterday Luca went to the market.",
    rule_section="attenzione",
)
GRADE_OK = Grade(
    task_done=True,
    rule_correct=True,
    important_errors=0,
    verdict="correct",
    score=0.9,
    feedback="Perfetto.",
    hint="",
    errors=[],
    corrected="Yesterday Luca went to the market.",
    rule_section="regola",
)
MEMORY = TopicMemory(
    strengths=["struttura della frase"],
    weaknesses=["verbi irregolari"],
    next_focus="Past simple di go e see.",
    story_so_far="Luca è a Londra e va al mercato.",
)
