"""The grader agent (writing answers) and the memory agent (topic memory)."""

import json
import re
from typing import Any

from datapizza.agents import Agent

from enita.agent.clients import get_client
from enita.agent.formats import normalize, words
from enita.agent.pipeline import GenerationError, _structured
from enita.agent.prompts import GRADER_SYSTEM, GRADER_TASK, MEMORY_SYSTEM, MEMORY_TASK
from enita.guardrails.checks import injection_reasons
from enita.models import ExerciseDraft, Grade, TopicCard, TopicMemory
from enita.settings import Settings

GENERIC_HINT = "Rileggi la regola della scheda e controlla il verbo principale."


def default_grader(settings: Settings) -> Any:
    # No tools: a prompt injection in the student's text has nothing to call.
    return Agent(
        name="grader",
        client=get_client(settings, settings.verifier_model),
        system_prompt=GRADER_SYSTEM,
        output_cls=Grade,
        max_steps=1,
    )


def default_memory_agent(settings: Settings) -> Any:
    return Agent(
        name="memory",
        client=get_client(settings),
        system_prompt=MEMORY_SYSTEM,
        output_cls=TopicMemory,
        max_steps=1,
    )


def mask_solution(text: str, student_answer: str, answers: list[str]) -> str:
    """While the exercise is open, hide the words of the model answers that the student has
    not written yet ("il passato di buy è bought" → "il passato di buy è …")."""
    written = {w.lower() for w in words(student_answer)}
    secret = {
        w.lower() for a in answers for w in words(a) if len(w) > 2 and w.lower() not in written
    }
    if not secret:
        return text
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, sorted(secret))) + r")\b", re.IGNORECASE)
    return pattern.sub("…", text)


def _escape(answer: str) -> str:
    """The answer cannot close the data block."""
    return answer.replace("<", "‹").replace(">", "›")


def decide(task_done: bool, rule_correct: bool, important_errors: int) -> tuple[str, float]:
    """The code, not the LLM, turns the three judgements into the verdict and the score."""
    if not task_done or not rule_correct:
        return "wrong", 0.2 if task_done or rule_correct else 0.0
    if important_errors > 0:
        return "partial", max(0.5, 0.8 - 0.1 * important_errors)
    return "correct", 1.0


def safe_grade(grade: Grade, draft: ExerciseDraft) -> Grade:
    """Output guardrail on the grader: verdict and score from the judgements, no leaked
    solution in the hint, no AI instructions in the texts."""
    verdict, score = decide(grade.task_done, grade.rule_correct, max(grade.important_errors, 0))
    hint = "" if verdict == "correct" else grade.hint
    if any(normalize(a) and normalize(a) in normalize(hint) for a in draft.answers):
        hint = GENERIC_HINT
    texts = [grade.feedback, hint, grade.corrected, *grade.errors]
    if any(injection_reasons(t) for t in texts):
        raise GenerationError("The grade contains instructions for an AI system.")
    return grade.model_copy(update={"verdict": verdict, "score": round(score, 2), "hint": hint})


async def grade_answer(
    grader: Any, card: TopicCard, draft: ExerciseDraft, answer: str, history: list[dict]
) -> Grade:
    task = GRADER_TASK.format(
        title=card.title,
        level=card.level,
        type=draft.type,
        instruction=draft.instruction,
        prompt=draft.prompt,
        criteria="; ".join(draft.criteria),
        answers=" | ".join(draft.answers),
        history=json.dumps(
            [{"verdict": h["verdict"], "notes": h["notes"]} for h in history], ensure_ascii=False
        )
        or "[]",
        answer=_escape(answer),
    )
    return safe_grade(_structured(await grader.a_run(task), Grade), draft)


async def rewrite_memory(
    agent: Any, card: TopicCard, previous: TopicMemory | None, exercises: list[dict]
) -> TopicMemory:
    task = MEMORY_TASK.format(
        title=card.title,
        level=card.level,
        memory=previous.model_dump_json(exclude={"updated_at"}) if previous else "{}",
        exercises=json.dumps(exercises, ensure_ascii=False),
    )
    memory = _structured(await agent.a_run(task), TopicMemory)
    texts = [*memory.strengths, *memory.weaknesses, memory.next_focus, memory.story_so_far]
    if any(injection_reasons(t) for t in texts):
        raise GenerationError("The memory contains instructions for an AI system.")
    return memory.model_copy(
        update={"strengths": memory.strengths[:4], "weaknesses": memory.weaknesses[:4]}
    )
