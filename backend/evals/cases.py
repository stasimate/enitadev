"""Eval cases for the exercise review (rules check + verifier agent + decision).

Each case is a draft with a known defect (or no defect) and the expected decision.
The verifier is an LLM-as-judge with a rubric (prompts.VERIFIER_SYSTEM).
"""

from dataclasses import dataclass

from enita.models import ExerciseDraft


@dataclass(frozen=True)
class ReviewCase:
    id: str
    topic_id: str
    draft: ExerciseDraft
    expect_approved: bool
    defect: str
    edge: bool = False  # a known hard case for LLM judges


def _d(**kw) -> ExerciseDraft:
    base = {"options": [], "correction": "", "rule_section": "regola"}
    return ExerciseDraft(**{**base, **kw})


REVIEW_CASES: list[ReviewCase] = [
    ReviewCase(
        id="good-fill-present-simple",
        topic_id="present-simple",
        draft=_d(
            type="fill_blank",
            instruction="Completa con la forma corretta del verbo tra parentesi.",
            prompt="My father ___ (work) in a hospital.",
            answers=["works"],
            explanation="Con he/she/it il present simple aggiunge -s al verbo.",
        ),
        expect_approved=True,
        defect="none",
    ),
    ReviewCase(
        id="good-choice-past-simple",
        topic_id="past-simple",
        draft=_d(
            type="multiple_choice",
            instruction="Scegli la forma corretta.",
            prompt="Yesterday we ___ to the cinema.",
            options=["go", "went", "goed", "gone"],
            answers=["went"],
            rule_section="attenzione",
            explanation="Go è irregolare: il past simple è went, non goed.",
        ),
        expect_approved=True,
        defect="none",
    ),
    ReviewCase(
        id="wrong-answer-irregular-participle",
        topic_id="present-perfect",
        draft=_d(
            type="fill_blank",
            instruction="Completa con il present perfect del verbo tra parentesi.",
            prompt="I have ___ (read) that book twice.",
            answers=["readed"],
            explanation="Il participio di read si forma con -ed.",
        ),
        expect_approved=False,
        defect="the expected answer is wrong English (readed)",
    ),
    ReviewCase(
        id="two-correct-options",
        topic_id="present-simple",
        draft=_d(
            type="multiple_choice",
            instruction="Scegli il verbo corretto.",
            prompt="She ___ to school every day.",
            options=["goes", "walks", "go"],
            answers=["goes"],
            explanation="Alla terza persona singolare si aggiunge -s o -es.",
        ),
        expect_approved=False,
        defect="'walks' is also correct",
    ),
    ReviewCase(
        id="repeated-words",
        topic_id="present-perfect",
        draft=_d(
            type="fill_blank",
            instruction="Completa con il present perfect.",
            prompt="He ___ finished his homework.",
            answers=["has finished"],
            explanation="Il present perfect si forma con has + participio.",
        ),
        expect_approved=False,
        defect="the answer repeats 'finished'",
    ),
    ReviewCase(
        id="explanation-contradicts-card",
        topic_id="present-continuous",
        draft=_d(
            type="fill_blank",
            instruction="Completa con la forma corretta del verbo tra parentesi.",
            prompt="Look! It ___ (rain) now.",
            answers=["is raining", "'s raining"],
            explanation="Per le azioni in corso adesso si usa il past simple.",
        ),
        expect_approved=False,
        defect="the explanation names the wrong tense",
    ),
    ReviewCase(
        id="leaked-solution",
        topic_id="comparatives-superlatives",
        draft=_d(
            type="fill_blank",
            instruction="Completa con 'bigger', il comparativo di big.",
            prompt="An elephant is ___ (big) than a horse.",
            answers=["bigger"],
            explanation="Big raddoppia la g: bigger.",
        ),
        expect_approved=False,
        defect="the instruction shows the solution",
    ),
    ReviewCase(
        id="edge-article-ambiguity",
        topic_id="articles",
        draft=_d(
            type="multiple_choice",
            instruction="Scegli l'articolo corretto.",
            prompt="I saw ___ cat in the garden.",
            options=["a", "an", "the"],
            answers=["a"],
            explanation="Si usa a davanti a un suono di consonante.",
        ),
        expect_approved=False,
        defect="'the' also gives a correct sentence",
        edge=True,
    ),
]

REVIEW_CASES += [
    ReviewCase(
        id="good-find-error",
        topic_id="present-simple",
        draft=_d(
            type="find_error",
            instruction="Trova la parola sbagliata.",
            prompt="My sister don't like coffee.",
            answers=["don't"],
            correction="doesn't",
            rule_section="attenzione",
            explanation="Con he/she/it la negazione usa doesn't.",
        ),
        expect_approved=True,
        defect="none",
    ),
    ReviewCase(
        id="find-error-two-errors",
        topic_id="past-simple",
        draft=_d(
            type="find_error",
            instruction="Trova la parola sbagliata.",
            prompt="Yesterday he goed to the cinema and buyed a ticket.",
            answers=["goed"],
            correction="went",
            explanation="Go è irregolare: went.",
        ),
        expect_approved=False,
        defect="'buyed' is also wrong",
    ),
    ReviewCase(
        id="transform-wrong-answer",
        topic_id="present-simple",
        draft=_d(
            type="transform",
            instruction="Volgi la frase alla forma negativa.",
            prompt="He plays tennis on Sundays.",
            answers=["He doesn't plays tennis on Sundays."],
            explanation="Con doesn't il verbo resta alla forma base.",
        ),
        expect_approved=False,
        defect="the expected answer is wrong English (doesn't plays)",
    ),
]

# Topics for the trajectory eval (real generation through MCP).
TRAJECTORY_TOPICS: list[tuple[str, str]] = [
    ("present-simple", "find_error"),
    ("past-simple", "reorder"),
    ("comparatives-superlatives", "transform"),
]
