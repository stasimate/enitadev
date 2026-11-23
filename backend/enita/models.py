"""Pydantic schemas that the API, the agent and the MCP server share."""

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["A1", "A2", "B1", "B2"]
SectionSlug = Literal["regola", "esempi", "attenzione", "riepilogo"]
ExerciseType = Literal[
    "fill_blank",
    "multiple_choice",
    "reorder",
    "transform",
    "find_error",
    "translate",
    "guided",
    "rewrite",
    "dialogue",
]
CLOSED_TYPES: tuple[str, ...] = (
    "fill_blank",
    "multiple_choice",
    "reorder",
    "transform",
    "find_error",
)
WRITING_TYPES: tuple[str, ...] = ("translate", "guided", "rewrite", "dialogue")
Verdict = Literal["correct", "partial", "wrong"]

SECTION_SLUGS: tuple[str, ...] = ("regola", "esempi", "attenzione", "riepilogo")
BLANK = "___"
MAX_ANSWER_LENGTH = 600  # writing answers have 2-4 sentences
MAX_PROMPT_LENGTH = 400
MAX_ATTEMPTS = 3  # the solution appears after this number of attempts


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
        description=(
            f"fill_blank / multiple_choice: one English sentence with '{BLANK}' one time. "
            "reorder: the Italian translation of the target sentence. "
            "transform: the English source sentence. "
            "find_error: one English sentence with exactly one wrong word. "
            "translate: 1-2 Italian sentences to translate. guided: the writing task, in "
            "Italian. rewrite: a short English text to rewrite. dialogue: one line of a "
            "character, as 'Name: text'."
        )
    )
    context: str = Field(
        description=(
            "One Italian sentence about the ongoing story of this topic, that this exercise "
            "continues (characters and situation). Empty string if there is no story."
        )
    )
    options: list[str] = Field(
        description="multiple_choice: 3 or 4 choices. All other types: empty list."
    )
    answers: list[str] = Field(
        description=(
            "All the accepted answers. multiple_choice: exactly one, equal to an option. "
            "reorder: the target sentence(s). transform: the transformed sentence(s). "
            "find_error: exactly one item, the wrong word as it is in the prompt. "
            "Writing types: 1-3 model answers (good, natural answers at the level)."
        )
    )
    criteria: list[str] = Field(
        description=(
            "Writing types: 2-4 short points that the grader must check (the target rule "
            "and the task). Closed types: empty list."
        )
    )
    correction: str = Field(
        description=(
            "find_error: the correct form of the wrong word, or an empty string if the word "
            "must be removed. Other types: empty string."
        )
    )
    rule_section: SectionSlug = Field(
        description="The section of the theory card that the exercise practises."
    )
    explanation: str = Field(
        description="Why the answer is correct, in Italian, 1-3 sentences, with the rule."
    )


class Verification(BaseModel):
    """The decision of the verifier agent about one draft."""

    correct_options: list[str] = Field(
        description=(
            "multiple_choice: copy EVERY option that gives a grammatically correct English "
            "sentence when you put it in the blank, in any context. fill_blank: empty list."
        )
    )
    approved: bool
    issues: list[str] = Field(description="The problems found. Empty when approved.")


class Explanation(BaseModel):
    """The output of the explainer agent ("Spiegami meglio")."""

    explanation: str = Field(
        description="Markdown in Italian, 80-180 words, with English examples in backticks."
    )
    sources: list[str] = Field(
        description="The rule_ref values (topic#section) of the passages used. At least one."
    )


class Grade(BaseModel):
    """The output of the grader agent for one writing attempt. The code computes the verdict
    and the score from task_done, rule_correct and important_errors (see tutor.safe_grade)."""

    task_done: bool = Field(description="The student did what the instruction asks.")
    rule_correct: bool = Field(description="Every use of the target rule is correct.")
    important_errors: int = Field(description="Other errors that change the grammar.")
    verdict: Verdict = Field(description="Your verdict (the app recomputes it).")
    score: float = Field(description="0.0 to 1.0 (the app recomputes it).")
    feedback: str = Field(
        description="Italian, 1-3 sentences, specific to the student's words. Start with what "
        "is good."
    )
    hint: str = Field(
        description="Italian hint to fix the answer WITHOUT the corrected words. Empty when "
        "the verdict is correct."
    )
    errors: list[str] = Field(description="Short Italian notes, one for each error. May be empty.")
    corrected: str = Field(
        description="The student's text with the minimum corrections (keep their content)."
    )
    rule_section: SectionSlug = Field(
        description="The card section most related to the main error (or to the exercise)."
    )


class TopicMemory(BaseModel):
    """What the tutor remembers about the student on one topic. The memory agent rewrites it."""

    strengths: list[str] = Field(
        description="Max 4 short Italian points: what the student does well."
    )
    weaknesses: list[str] = Field(description="Max 4 short Italian points: recurring errors.")
    next_focus: str = Field(description="One Italian sentence: what the next exercise practises.")
    story_so_far: str = Field(
        description="Max 3 Italian sentences: the story of the exercises (characters, events)."
    )
    updated_at: str = ""


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
    context: str = ""


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)


class Feedback(BaseModel):
    """Internal result of the fixed-rule check of a closed exercise."""

    verdict: Verdict
    score: float
    correct_answer: str
    explanation: str
    rule_ref: str


class Solution(BaseModel):
    model_answer: str
    corrected: str | None = None  # writing types: the student's last text, corrected
    explanation: str


class AttemptFeedback(BaseModel):
    attempt: int
    verdict: Verdict
    score: float
    feedback: str
    hint: str | None
    errors: list[str]
    rule_ref: str
    done: bool
    solution: Solution | None


class TopicProgress(BaseModel):
    topic_id: str
    attempts: int
    correct: int
    accuracy: float


class LearnerProfile(BaseModel):
    """Permanent memory of the student (RF-20). It contains aggregates only."""

    topics: list[TopicProgress] = []
    frequent_errors: dict[str, int] = Field(
        default_factory=dict, description="rule_ref → number of wrong answers"
    )
    streak_days: int = 0
    active_days: list[str] = Field(
        default_factory=list, description="ISO dates of the last 30 days with an attempt"
    )
    memories: dict[str, TopicMemory] = Field(default_factory=dict)


class Source(BaseModel):
    rule_ref: str
    title: str


class ExplainResponse(BaseModel):
    explanation: str
    sources: list[Source]
