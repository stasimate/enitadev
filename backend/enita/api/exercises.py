"""Exercise endpoints: make an exercise and check an answer."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from enita.agent.clients import ProviderConfigError
from enita.agent.pipeline import GenerationError
from enita.api.topics import get_content
from enita.models import AnswerRequest, Exercise, ExerciseRequest, Feedback
from enita.practice.service import ExerciseNotFound, PracticeService, TopicNotFound
from enita.settings import get_settings
from enita.storage.exercises import ExerciseStore

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@lru_cache
def get_practice() -> PracticeService:
    return PracticeService(get_settings(), get_content(), ExerciseStore())


Practice = Annotated[PracticeService, Depends(get_practice)]


@router.post("")
async def create_exercise(req: ExerciseRequest, practice: Practice) -> Exercise:
    try:
        return await practice.create(req.topic_id, req.type)
    except TopicNotFound:
        raise HTTPException(404, f"Topic '{req.topic_id}' not found") from None
    except ProviderConfigError as exc:
        raise HTTPException(503, str(exc)) from None
    except GenerationError as exc:
        log.warning("Exercise generation failed: %s", exc)
        raise HTTPException(502, "The tutor did not make a valid exercise.") from None


@router.post("/{exercise_id}/answer")
def answer_exercise(exercise_id: str, req: AnswerRequest, practice: Practice) -> Feedback:
    try:
        return practice.answer(exercise_id, req.answer)
    except ExerciseNotFound:
        raise HTTPException(404, f"Exercise '{exercise_id}' not found") from None
