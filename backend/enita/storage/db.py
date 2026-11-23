"""SQLite persistence: exercises, attempts (permanent memory) and the audit trail."""

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from enita.agent.formats import completed_sentence
from enita.models import ExerciseDraft, Feedback, LearnerProfile, TopicProgress
from enita.storage.exercises import StoredExercise

SCHEMA = """
CREATE TABLE IF NOT EXISTS exercises (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    draft TEXT NOT NULL,
    created_at TEXT NOT NULL,
    served INTEGER NOT NULL DEFAULT 1
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


def streak(active_days: list[str], today: date) -> int:
    """Consecutive active days that end today (or yesterday, if today has no attempt yet)."""
    days = set(active_days)
    day = today if today.isoformat() in days else today - timedelta(days=1)
    count = 0
    while day.isoformat() in days:
        count += 1
        day -= timedelta(days=1)
    return count


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)
            # Migration for databases made before the exercise pool.
            cols = {r["name"] for r in c.execute("PRAGMA table_info(exercises)")}
            if "served" not in cols:
                c.execute("ALTER TABLE exercises ADD COLUMN served INTEGER NOT NULL DEFAULT 1")

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

    def add_exercise(
        self, topic_id: str, draft: ExerciseDraft, served: bool = True
    ) -> StoredExercise:
        """Save an approved exercise. served=False puts it in the pool for later."""
        item = StoredExercise(id=uuid.uuid4().hex, topic_id=topic_id, draft=draft)
        with self._conn() as c:
            c.execute(
                "INSERT INTO exercises (id, topic_id, draft, created_at, served) "
                "VALUES (?, ?, ?, ?, ?)",
                (item.id, topic_id, draft.model_dump_json(), _now(), int(served)),
            )
        return item

    def take_pooled(self, topic_id: str, exercise_type: str | None = None) -> StoredExercise | None:
        """Take the oldest exercise of the pool for a topic and mark it as served."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, topic_id, draft FROM exercises WHERE topic_id = ? AND served = 0 "
                "ORDER BY created_at, rowid",
                (topic_id,),
            ).fetchall()
            for row in rows:
                draft = ExerciseDraft.model_validate_json(row["draft"])
                if exercise_type is None or draft.type == exercise_type:
                    c.execute("UPDATE exercises SET served = 1 WHERE id = ?", (row["id"],))
                    return StoredExercise(id=row["id"], topic_id=topic_id, draft=draft)
        return None

    def recent_exercises(self, topic_id: str, limit: int = 10) -> list[str]:
        """The solved sentences of the latest exercises of a topic (written by the agents)."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT draft FROM exercises WHERE topic_id = ? "
                "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (topic_id, limit),
            ).fetchall()
        drafts = [ExerciseDraft.model_validate_json(r["draft"]) for r in rows]
        return [f"{d.type}: {completed_sentence(d)}" for d in drafts]

    def count_pooled(self, topic_id: str) -> int:
        with self._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) n FROM exercises WHERE topic_id = ? AND served = 0", (topic_id,)
            ).fetchone()
        return int(row["n"])

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
            days = [
                r["d"]
                for r in c.execute(
                    "SELECT DISTINCT substr(created_at, 1, 10) d FROM attempts "
                    "WHERE flagged = 0 AND created_at >= ? ORDER BY d",
                    ((date.today() - timedelta(days=29)).isoformat(),),
                ).fetchall()
            ]
        return LearnerProfile(
            streak_days=streak(days, date.today()),
            active_days=days,
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
