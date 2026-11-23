"""Pydantic schemas that the API, the agent and the MCP server share."""

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["A1", "A2", "B1"]
SectionSlug = Literal["regola", "esempi", "attenzione", "riepilogo"]
ExerciseType = Literal["fill_blank", "multiple_choice"]
Verdict = Literal["correct", "partial", "wrong"]

SECTION_SLUGS: tuple[str, ...] = ("regola", "esempi", "attenzione", "riepilogo")
BLANK = "___"
MAX_ANSWER_LENGTH = 300


class TopicSummary(BaseModel):
    id: str
    title: str
    level: Level
    tags: list[str] = []


class Section(BaseModel):
    slug: str
    title: str
    markdown: str


class TopicCard(TopicSummary):
    sections: list[Section]

    def has_section(self, slug: str) -> bool:
        return any(s.slug == slug for s in self.sections)

    def as_markdown(self) -> str:
        parts = [f"# {self.title} ({self.level})"]
        parts += [f"## {s.title}\n{s.markdown}" for s in self.sections]
        return "\n\n".join(parts)


# --- Agent outputs (structured output of the writer and the verifier) ------------------


class ExerciseDraft(BaseModel):
    """The exercise that the writer agent makes. It contains the solution."""

    type: ExerciseType
    instruction: str = Field(description="Short instruction for the student, in Italian.")
    prompt: str = Field(
        description=f"One English sentence. For fill_blank it contains '{BLANK}' one time."
    )
    options: list[str] = Field(
        description="multiple_choice: 3 or 4 choices. fill_blank: empty list."
    )
    answers: list[str] = Field(
        description="All the accepted answers. multiple_choice: exactly one, equal to an option."
    )
    rule_section: SectionSlug = Field(
        description="The section of the theory card that the exercise practises."
    )
    explanation: str = Field(
        description="Why the answer is correct, in Italian, 1-3 sentences, with the rule."
    )


class Verification(BaseModel):
    """The decision of the verifier agent about one draft."""

    approved: bool
    issues: list[str] = Field(description="The problems found. Empty when approved.")


# --- API models ------------------------------------------------------------------------


class ExerciseRequest(BaseModel):
    topic_id: str
    type: ExerciseType | None = None


class Exercise(BaseModel):
    """The public exercise. It never contains the solution."""

    id: str
    topic_id: str
    type: ExerciseType
    instruction: str
    prompt: str
    options: list[str]


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)


class Feedback(BaseModel):
    verdict: Verdict
    score: float
    correct_answer: str
    explanation: str
    rule_ref: str
