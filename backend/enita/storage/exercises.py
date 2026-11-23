"""Exercise storage. In memory for M2. Milestone M3 moves it to SQLite."""

import uuid
from dataclasses import dataclass

from enita.models import Exercise, ExerciseDraft


@dataclass(frozen=True)
class StoredExercise:
    id: str
    topic_id: str
    draft: ExerciseDraft

    def public(self) -> Exercise:
        """The exercise for the frontend, without the solution."""
        return Exercise(
            id=self.id,
            topic_id=self.topic_id,
            type=self.draft.type,
            instruction=self.draft.instruction,
            prompt=self.draft.prompt,
            options=self.draft.options,
        )


class ExerciseStore:
    def __init__(self) -> None:
        self._items: dict[str, StoredExercise] = {}

    def add(self, topic_id: str, draft: ExerciseDraft) -> StoredExercise:
        item = StoredExercise(id=uuid.uuid4().hex, topic_id=topic_id, draft=draft)
        self._items[item.id] = item
        return item

    def get(self, exercise_id: str) -> StoredExercise | None:
        return self._items.get(exercise_id)
