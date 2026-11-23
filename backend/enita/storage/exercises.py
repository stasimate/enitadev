"""The stored exercise (with its solution) and its public view."""

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
            context=self.draft.context,
        )
