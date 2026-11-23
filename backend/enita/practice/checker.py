"""Fixed-rule check of closed exercises (RF-12). The LLM never decides correctness here."""

import re

from enita.models import ExerciseDraft, Feedback

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Lowercase, straight quotes, one space between words, no final punctuation."""
    text = _SPACES.sub(" ", text.translate(_QUOTES).strip().lower())
    return text.rstrip(".!?;,").strip()


def check_answer(draft: ExerciseDraft, topic_id: str, answer: str) -> Feedback:
    correct = normalize(answer) in {normalize(a) for a in draft.answers}
    return Feedback(
        verdict="correct" if correct else "wrong",
        score=1.0 if correct else 0.0,
        correct_answer=draft.answers[0],
        explanation=draft.explanation,
        rule_ref=f"{topic_id}#{draft.rule_section}",
    )
