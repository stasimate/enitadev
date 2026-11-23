"""SQLite persistence: exercises, attempts (permanent memory) and the audit trail."""

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from enita.models import ExerciseDraft, Feedback, LearnerProfile, TopicProgress
from enita.storage.exercises import StoredExercise

SCHEMA = """
CREATE TABLE IF NOT EXISTS exercises (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    draft TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    id TEXT PRIMARY KEY,
    exercise_id TEXT NOT NULL REFERENCES exercises(id),
    topic_id TEXT NOT NULL,
    answer TEXT NOT NULL,
    verdict TEXT NOT NULL,
    score REAL NOT NULL,
    rule_ref TEXT NOT NULL,
    flagged INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id TEXT PRIMARY KEY,
    event TEXT NOT NULL,
    topic_id TEXT,
    outcome TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS attempts_topic ON attempts(topic_id);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- Exercises ---------------------------------------------------------------------

    def add_exercise(self, topic_id: str, draft: ExerciseDraft) -> StoredExercise:
        item = StoredExercise(id=uuid.uuid4().hex, topic_id=topic_id, draft=draft)
        with self._conn() as c:
            c.execute(
                "INSERT INTO exercises VALUES (?, ?, ?, ?)",
                (item.id, topic_id, draft.model_dump_json(), _now()),
            )
        return item

    def get_exercise(self, exercise_id: str) -> StoredExercise | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
        if row is None:
            return None
        draft = ExerciseDraft.model_validate_json(row["draft"])
        return StoredExercise(id=row["id"], topic_id=row["topic_id"], draft=draft)

    # --- Attempts and profile ----------------------------------------------------------

    def add_attempt(
        self, item: StoredExercise, answer: str, feedback: Feedback, flagged: bool = False
    ) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex,
                    item.id,
                    item.topic_id,
                    answer,
                    feedback.verdict,
                    feedback.score,
                    feedback.rule_ref,
                    int(flagged),
                    _now(),
                ),
            )

    def profile(self, topic_id: str | None = None) -> LearnerProfile:
        """Aggregates only. Never the raw answers: they are untrusted text (see guardrails).

        Flagged attempts (guardrail) are not learning data. The audit trail keeps them.
        """
        where, args = (
            ("WHERE flagged = 0 AND topic_id = ?", (topic_id,))
            if topic_id
            else ("WHERE flagged = 0", ())
        )
        with self._conn() as c:
            topics = c.execute(
                f"SELECT topic_id, COUNT(*) n, SUM(score) ok FROM attempts {where} "
                "GROUP BY topic_id ORDER BY topic_id",
                args,
            ).fetchall()
            errors = c.execute(
                f"SELECT rule_ref, COUNT(*) n FROM attempts {where} "
                "AND verdict != 'correct' "
                "GROUP BY rule_ref ORDER BY n DESC, rule_ref LIMIT 5",
                args,
            ).fetchall()
        return LearnerProfile(
            topics=[
                TopicProgress(
                    topic_id=r["topic_id"],
                    attempts=r["n"],
                    correct=int(r["ok"] or 0),
                    accuracy=round((r["ok"] or 0) / r["n"], 2),
                )
                for r in topics
            ],
            frequent_errors={r["rule_ref"]: r["n"] for r in errors},
        )

    # --- Audit trail -------------------------------------------------------------------

    def add_audit(
        self, event: str, outcome: str, data: dict[str, Any], topic_id: str | None = None
    ) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, event, topic_id, outcome, json.dumps(data), _now()),
            )

    def list_audit(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM audit ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{**dict(r), "data": json.loads(r["data"])} for r in rows]
