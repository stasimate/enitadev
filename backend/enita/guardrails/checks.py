"""Guardrails (RNF-03): validation of the student input and of the agent output."""

import re
import unicodedata
from dataclasses import dataclass, field

from enita.models import MAX_ANSWER_LENGTH

# Known prompt-injection patterns. The list is small on purpose: it flags, it does not block
# the application. The main defence is the design: raw answers never reach an LLM prompt.
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        (
            r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|above|prior|all)\b.{0,30}"
            r"\b(instructions?|prompts?|rules?)\b"
        ),
        r"\byou are now\b",
        r"\b(system|developer) (prompt|message)\b",
        r"\bact as\b",
        r"</?\s*(system|assistant|user|tool)\s*>",
        r"\b(approve|mark)\b.{0,20}\b(correct|approved)\b",
        r"\bignora\b.{0,30}\bistruzioni\b",
    )
)


@dataclass
class GuardrailResult:
    text: str
    flagged: bool = False
    reasons: list[str] = field(default_factory=list)


def _clean(text: str) -> str:
    """Remove control and format characters. Keep one space between words."""
    kept = "".join(
        " " if ch.isspace() else ch
        for ch in text
        if ch.isspace() or unicodedata.category(ch) not in ("Cc", "Cf")
    )
    return re.sub(r"\s+", " ", kept).strip()


def injection_reasons(text: str) -> list[str]:
    return [f"pattern: {p.pattern[:40]}" for p in INJECTION_PATTERNS if p.search(text)]


def validate_answer(raw: str) -> GuardrailResult:
    """Input guardrail for the student answer."""
    text = _clean(raw)[:MAX_ANSWER_LENGTH]
    reasons = injection_reasons(text)
    return GuardrailResult(text=text, flagged=bool(reasons), reasons=reasons)


def output_issues(instruction: str, prompt: str, explanation: str, answers: list[str]) -> list[str]:
    """Output guardrail for the writer: no leaked solution, no injected instructions."""
    issues: list[str] = []
    visible = f"{instruction} {prompt}".lower()
    if any(len(a) > 2 and re.search(rf"\b{re.escape(a.lower())}\b", visible) for a in answers):
        issues.append("The instruction or the prompt shows the solution.")
    if injection_reasons(f"{instruction} {prompt} {explanation}"):
        issues.append("The exercise text contains instructions for an AI system.")
    if "<" in visible or "http" in visible:
        issues.append("The exercise text must not contain HTML or links.")
    return issues
