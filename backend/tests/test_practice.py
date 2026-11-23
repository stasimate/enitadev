import pytest
from fastapi.testclient import TestClient

from enita.agent.pipeline import GenerationError, generate_exercise, rule_issues
from enita.api.exercises import get_practice
from enita.api.topics import get_content
from enita.main import app
from enita.practice.checker import check_answer, normalize
from enita.practice.service import PracticeService
from enita.settings import get_settings
from enita.storage.exercises import ExerciseStore
from tests.fakes import APPROVE, CHOICE, FILL, REJECT, FakeAgent, no_tools

# --- Fixed-rule check -------------------------------------------------------------------


def test_normalize() -> None:
    assert normalize("  Doesn’t   WORK. ") == "doesn't work"


@pytest.mark.parametrize(
    ("answer", "verdict"), [("works", "correct"), (" Works! ", "correct"), ("work", "wrong")]
)
def test_check_answer(answer: str, verdict: str) -> None:
    fb = check_answer(FILL, "present-simple", answer)
    assert fb.verdict == verdict
    assert fb.rule_ref == "present-simple#regola"
    assert fb.correct_answer == "works"


def test_rule_issues() -> None:
    assert rule_issues(FILL) == []
    assert rule_issues(CHOICE) == []
    assert rule_issues(FILL.model_copy(update={"prompt": "No blank here."}))
    assert rule_issues(CHOICE.model_copy(update={"answers": ["Are"]}))
    assert rule_issues(CHOICE.model_copy(update={"options": ["Do", "do", "Is"]}))
    assert rule_issues(CHOICE, expected_type="fill_blank")


# --- Multi-agent pipeline ---------------------------------------------------------------


async def test_pipeline_approves_first_draft() -> None:
    writer, verifier = FakeAgent([FILL]), FakeAgent([APPROVE])
    result = await generate_exercise(
        writer, verifier, topic_id="present-simple", exercise_type="fill_blank", card="CARD"
    )
    assert result.attempts == 1 and result.draft == FILL
    assert "CARD" in verifier.tasks[0]


async def test_pipeline_retries_with_verifier_issues() -> None:
    writer, verifier = FakeAgent([FILL, FILL]), FakeAgent([REJECT, APPROVE])
    result = await generate_exercise(
        writer, verifier, topic_id="present-simple", exercise_type="fill_blank", card="C"
    )
    assert result.attempts == 2
    assert "Two answers are correct." in writer.tasks[1]


async def test_rules_check_overrides_verifier_approval() -> None:
    bad = FILL.model_copy(update={"prompt": "No blank."})
    writer, verifier = FakeAgent([bad]), FakeAgent([APPROVE])
    with pytest.raises(GenerationError):
        await generate_exercise(
            writer, verifier, topic_id="t", exercise_type="fill_blank", card="C", max_attempts=2
        )
    assert len(writer.tasks) == 2


# --- API flow -----------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    service = PracticeService(
        get_settings(),
        get_content(),
        ExerciseStore(),
        tools=no_tools,
        agents=lambda tools: (FakeAgent([CHOICE]), FakeAgent([APPROVE])),
    )
    app.dependency_overrides[get_practice] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_exercise_flow(client: TestClient) -> None:
    res = client.post(
        "/api/exercises", json={"topic_id": "present-simple", "type": "multiple_choice"}
    )
    assert res.status_code == 200
    ex = res.json()
    assert ex["type"] == "multiple_choice"
    assert "answers" not in ex and "explanation" not in ex  # never send the solution

    fb = client.post(f"/api/exercises/{ex['id']}/answer", json={"answer": "Do"}).json()
    assert fb["verdict"] == "wrong"
    assert fb["correct_answer"] == "Does"
    assert fb["rule_ref"] == "present-simple#attenzione"


def test_exercise_errors(client: TestClient) -> None:
    assert client.post("/api/exercises", json={"topic_id": "nope"}).status_code == 404
    assert client.post("/api/exercises/x/answer", json={"answer": "a"}).status_code == 404
    long = {"answer": "a" * 301}
    assert client.post("/api/exercises/x/answer", json=long).status_code == 422
