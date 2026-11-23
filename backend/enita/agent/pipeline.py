"""Multi-agent exercise generation: writer → (rules check ∥ verifier) → decision.

The graph is a datapizza DagPipeline. A DAG has no cycles, so the retry loop
(the verifier rejects → the writer makes a new draft) is outside the pipeline.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from datapizza.core.models import PipelineComponent
from datapizza.pipeline import DagPipeline
from pydantic import BaseModel

from enita.agent.formats import completed_sentence, format_issues, normalize, prepare
from enita.agent.prompts import VERIFIER_TASK, WRITER_FEEDBACK, WRITER_TASK
from enita.guardrails.checks import output_issues
from enita.models import MAX_ANSWER_LENGTH, ExerciseDraft, ExerciseType, Verification


class AgentLike(Protocol):
    """The part of datapizza.agents.Agent that the pipeline uses."""

    async def a_run(self, task_input: str, **kwargs: Any) -> Any: ...


class GenerationError(RuntimeError):
    """The agents did not make a valid exercise."""


def _structured(step: Any, cls: type[BaseModel]) -> BaseModel:
    """Get the structured output of an agent step. Fall back to JSON in the text."""
    if step is None:
        raise GenerationError(f"The agent returned no result for {cls.__name__}")
    for item in getattr(step, "structured_data", None) or []:
        return cls.model_validate(item.model_dump())
    try:
        return cls.model_validate_json(step.text)
    except Exception as exc:
        raise GenerationError(f"The agent output is not a valid {cls.__name__}") from exc


# --- Pipeline nodes --------------------------------------------------------------------


class WriterNode(PipelineComponent):
    def __init__(self, agent: AgentLike) -> None:
        self.agent = agent

    def _run(self, **kwargs: Any) -> ExerciseDraft:
        raise NotImplementedError("Use a_run: the writer calls MCP tools asynchronously")

    async def _a_run(
        self, topic_id: str, exercise_type: ExerciseType, feedback: str = ""
    ) -> ExerciseDraft:
        task = WRITER_TASK.format(topic_id=topic_id, exercise_type=exercise_type, feedback=feedback)
        step = await self.agent.a_run(task, tool_choice="required_first")
        return prepare(_structured(step, ExerciseDraft))


def rule_issues(draft: ExerciseDraft, expected_type: ExerciseType | None = None) -> list[str]:
    """Fixed-rule checks. They are free and catch the format errors of the writer."""
    issues: list[str] = []
    if expected_type and draft.type != expected_type:
        issues.append(f"The exercise type must be {expected_type}.")
    if len(draft.prompt) > MAX_ANSWER_LENGTH:
        issues.append("The prompt is too long.")
    if not draft.answers or any(not a.strip() for a in draft.answers):
        issues.append("There must be at least one non-empty answer.")
        return issues
    issues += format_issues(draft)
    # In find_error the wrong word is in the prompt by design: check only the instruction.
    visible_prompt = "" if draft.type == "find_error" else draft.prompt
    issues += output_issues(draft.instruction, visible_prompt, draft.explanation, draft.answers)
    return issues


def fill_blank(draft: ExerciseDraft) -> str:
    """Kept for the evals and tests: the solved sentence of any exercise type."""
    return completed_sentence(draft)


class RulesNode(PipelineComponent):
    def _run(self, draft: ExerciseDraft, expected_type: ExerciseType) -> list[str]:
        return rule_issues(draft, expected_type)

    async def _a_run(self, draft: ExerciseDraft, expected_type: ExerciseType) -> list[str]:
        return rule_issues(draft, expected_type)


class VerifierNode(PipelineComponent):
    def __init__(self, agent: AgentLike) -> None:
        self.agent = agent

    def _run(self, **kwargs: Any) -> Verification:
        raise NotImplementedError("Use a_run")

    async def _a_run(self, draft: ExerciseDraft, card: str) -> Verification:
        task = VERIFIER_TASK.format(
            card=card, draft=draft.model_dump_json(indent=2), completed=completed_sentence(draft)
        )
        return _structured(await self.agent.a_run(task), Verification)


@dataclass
class Decision:
    approved: bool
    issues: list[str] = field(default_factory=list)


def option_issues(draft: ExerciseDraft, verification: Verification) -> list[str]:
    """multiple_choice: the code, not the LLM, decides if the solution is unique."""
    if draft.type != "multiple_choice":
        return []
    correct = {normalize(o) for o in verification.correct_options}
    extra = correct - {normalize(a) for a in draft.answers}
    if extra:
        return [f"These options also give a correct sentence: {sorted(extra)}. Change them."]
    return []


class DecisionNode(PipelineComponent):
    def _decide(
        self, draft: ExerciseDraft, rule_issues: list[str], verification: Verification
    ) -> Decision:
        own = [*rule_issues, *option_issues(draft, verification)]
        issues = [*own, *verification.issues]
        return Decision(approved=verification.approved and not own, issues=issues)

    def _run(
        self, draft: ExerciseDraft, rule_issues: list[str], verification: Verification
    ) -> Decision:
        return self._decide(draft, rule_issues, verification)

    async def _a_run(
        self, draft: ExerciseDraft, rule_issues: list[str], verification: Verification
    ) -> Decision:
        return self._decide(draft, rule_issues, verification)


def build_pipeline(writer: AgentLike, verifier: AgentLike) -> DagPipeline:
    dag = DagPipeline()
    dag.add_module("writer", WriterNode(writer))
    dag.add_module("rules", RulesNode())
    dag.add_module("verifier", VerifierNode(verifier))
    dag.add_module("decision", DecisionNode())
    dag.connect("writer", "rules", target_key="draft")
    dag.connect("writer", "verifier", target_key="draft")
    dag.connect("writer", "decision", target_key="draft")
    dag.connect("rules", "decision", target_key="rule_issues")
    dag.connect("verifier", "decision", target_key="verification")
    return dag


# --- Orchestration with retry ------------------------------------------------------------


@dataclass
class GenerationResult:
    draft: ExerciseDraft
    attempts: int
    rejected: list[list[str]] = field(default_factory=list)


async def generate_exercise(
    writer: AgentLike,
    verifier: AgentLike,
    *,
    topic_id: str,
    exercise_type: ExerciseType,
    card: str,
    max_attempts: int = 2,
) -> GenerationResult:
    """Run the pipeline. If the decision rejects the draft, give the issues to the writer."""
    dag = build_pipeline(writer, verifier)
    feedback = ""
    rejected: list[list[str]] = []
    for attempt in range(1, max_attempts + 1):
        results = await dag.a_run(
            {
                "writer": {
                    "topic_id": topic_id,
                    "exercise_type": exercise_type,
                    "feedback": feedback,
                },
                "rules": {"expected_type": exercise_type},
                "verifier": {"card": card},
            }
        )
        draft: ExerciseDraft = results["writer"]
        decision: Decision = results["decision"]
        if decision.approved:
            return GenerationResult(draft=draft, attempts=attempt, rejected=rejected)
        rejected.append(decision.issues)
        feedback = WRITER_FEEDBACK.format(
            draft=json.dumps(draft.model_dump(), ensure_ascii=False),
            issues="\n".join(f"- {i}" for i in decision.issues),
        )
    raise GenerationError(f"No approved exercise after {max_attempts} attempts: {rejected[-1]}")
