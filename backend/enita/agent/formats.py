"""Type-specific logic of the exercise formats: preparation, fixed-rule checks, completed
sentence (for the verifier) and the correct-answer text (for the feedback).
"""

import random
import re

from enita.models import BLANK, WRITING_TYPES, ExerciseDraft

BLANK_TYPES = ("fill_blank", "multiple_choice")
_WORD = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")
_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Lowercase, straight quotes, one space between words, no final punctuation."""
    text = _SPACES.sub(" ", text.translate(_QUOTES).strip().lower())
    return text.rstrip(".!?;,").strip()


def words(text: str) -> list[str]:
    """The words of a sentence, without punctuation. Contractions stay one word."""
    return _WORD.findall(text.replace("’", "'"))


def prepare(draft: ExerciseDraft) -> ExerciseDraft:
    """Set the fields that code makes, not the LLM: the shuffled chunks and the word list."""
    if draft.type == "reorder" and draft.answers:
        chunks = words(draft.answers[0])
        shuffled = chunks[:]
        rng = random.Random(draft.answers[0])
        for _ in range(10):  # a shuffle equal to the solution is not an exercise
            rng.shuffle(shuffled)
            if shuffled != chunks:
                break
        return draft.model_copy(update={"options": shuffled})
    if draft.type == "find_error":
        return draft.model_copy(update={"options": words(draft.prompt)})
    return draft


def completed_sentence(draft: ExerciseDraft) -> str:
    """The sentence that the student must produce or that the exercise contains, solved."""
    if not draft.answers:
        return draft.prompt
    if draft.type in BLANK_TYPES:
        # Remove the base-word hint just after the blank: "She ___ (work)" → "She works".
        prompt = re.sub(rf"{re.escape(BLANK)}\s*\([^)]*\)", BLANK, draft.prompt, count=1)
        return prompt.replace(BLANK, draft.answers[0], 1)
    if draft.type == "find_error":
        # An empty correction means: remove the wrong word ("more faster" → "faster").
        pattern = rf"\b{re.escape(draft.answers[0])}\b" + (r"\s*" if not draft.correction else "")
        fixed = re.sub(pattern, draft.correction, draft.prompt, count=1, flags=re.IGNORECASE)
        return _SPACES.sub(" ", fixed).strip()
    return draft.answers[0]


def correct_answer_text(draft: ExerciseDraft) -> str:
    if draft.type == "find_error":
        fix = draft.correction or "(togli la parola)"
        return f"{draft.answers[0]} → {fix}"
    return draft.answers[0]


def is_correct(draft: ExerciseDraft, answer: str) -> bool:
    if draft.type == "reorder":
        given = [w.lower() for w in words(answer)]
        return any(given == [w.lower() for w in words(a)] for a in draft.answers)
    if draft.type == "find_error":
        given = words(answer)
        return len(given) == 1 and given[0].lower() == draft.answers[0].lower()
    return normalize(answer) in {normalize(a) for a in draft.answers}


def _repeats_context(prompt: str, answer: str) -> bool:
    """True if the answer repeats words just before or just after the blank."""
    before, _, after = prompt.partition(BLANK)
    ans = normalize(answer).split()
    prev, nxt = normalize(before).split(), normalize(after).split()
    return any(ans[-k:] == nxt[:k] or ans[:k] == prev[-k:] for k in range(1, len(ans) + 1))


def format_issues(draft: ExerciseDraft) -> list[str]:
    """Fixed-rule checks for each exercise type."""
    issues: list[str] = []
    if draft.type in WRITING_TYPES:
        if draft.options:
            issues.append(f"A {draft.type} exercise must have no options.")
        if not 2 <= len(draft.criteria) <= 4:
            issues.append("A writing exercise needs 2 to 4 criteria for the grader.")
        if not 1 <= len(draft.answers) <= 3:
            issues.append("A writing exercise needs 1 to 3 model answers.")
        if BLANK in draft.prompt:
            issues.append(f"A {draft.type} exercise must not contain '{BLANK}'.")
        if draft.type == "dialogue" and ":" not in draft.prompt:
            issues.append("A dialogue prompt is one line of a character: 'Name: text'.")
        return issues
    if draft.criteria:
        issues.append("A closed exercise must have no criteria.")
    blanks = draft.prompt.count(BLANK)
    if draft.type in BLANK_TYPES:
        if blanks != 1:
            issues.append(f"The prompt must contain '{BLANK}' exactly one time.")
        elif any(_repeats_context(draft.prompt, a) for a in draft.answers):
            issues.append(
                "The answer repeats a word of the prompt. "
                f"The completed sentence is: {completed_sentence(draft)}"
            )
    elif blanks:
        issues.append(f"A {draft.type} exercise must not contain '{BLANK}'.")

    if draft.type == "fill_blank" and draft.options:
        issues.append("A fill_blank exercise must have no options.")

    if draft.type == "multiple_choice":
        options = [normalize(o) for o in draft.options]
        if not 3 <= len(options) <= 4 or len(set(options)) != len(options):
            issues.append("A multiple_choice exercise must have 3 or 4 different options.")
        if len(draft.answers) != 1 or normalize(draft.answers[0]) not in options:
            issues.append("A multiple_choice exercise must have one answer equal to an option.")

    if draft.type == "reorder" and draft.answers:
        target = sorted(w.lower() for w in words(draft.answers[0]))
        if not 3 <= len(target) <= 12:
            issues.append("A reorder sentence must have 3 to 12 words.")
        if any(sorted(w.lower() for w in words(a)) != target for a in draft.answers):
            issues.append("All the reorder answers must use the same words.")

    if draft.type == "transform" and normalize(draft.prompt) in {
        normalize(a) for a in draft.answers
    }:
        issues.append("The transformed sentence must be different from the source sentence.")

    if draft.type == "find_error":
        prompt_words = [w.lower() for w in words(draft.prompt)]
        wrong = words(draft.answers[0]) if len(draft.answers) == 1 else []
        if len(wrong) != 1 or prompt_words.count(wrong[0].lower()) != 1:
            issues.append("find_error needs one answer: a word that is in the prompt one time.")
        if draft.answers and normalize(draft.correction) == normalize(draft.answers[0]):
            issues.append("find_error needs a correction that is different from the wrong word.")
    return issues


def too_similar(prompt: str, recent: list[str], limit: float = 0.7) -> str | None:
    """Return the recent prompt that the new prompt repeats (word overlap >= limit), if any."""
    new = {w.lower() for w in words(prompt)}
    for old in recent:
        seen = {w.lower() for w in words(old)}
        if new and seen and len(new & seen) / len(new | seen) >= limit:
            return old
    return None
