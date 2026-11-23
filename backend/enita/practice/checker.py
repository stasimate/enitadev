"""Fixed-rule check of closed exercises (RF-12). The LLM never decides correctness here."""

from enita.agent.formats import correct_answer_text, is_correct, normalize
from enita.models import ExerciseDraft, Feedback

__all__ = ["check_answer", "normalize"]


def check_answer(draft: ExerciseDraft, topic_id: str, answer: str) -> Feedback:
    correct = is_correct(draft, answer)
    return Feedback(
        verdict="correct" if correct else "wrong",
        score=1.0 if correct else 0.0,
        correct_answer=correct_answer_text(draft),
        explanation=draft.explanation,
        rule_ref=f"{topic_id}#{draft.rule_section}",
    )
