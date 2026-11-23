"""Exercise endpoints: make an exercise and check an answer."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from enita.agent.clients import ProviderConfigError
from enita.agent.pipeline import GenerationError
from enita.api.topics import get_content
from enita.models import AnswerRequest, Exercise, ExerciseRequest, Feedback
from enita.practice.service import (
    ExerciseNotFound,
    GenerationTimeout,
    PracticeService,
    ProviderCallError,
    TopicNotFound,
)
from enita.settings import get_settings
from enita.storage.db import Database

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@lru_cache
def get_db() -> Database:
    return Database(get_settings().db_path)


@lru_cache
def get_practice() -> PracticeService:
    return PracticeService(get_settings(), get_content(), get_db())


Practice = Annotated[PracticeService, Depends(get_practice)]


@router.post("")
async def create_exercise(req: ExerciseRequest, practice: Practice) -> Exercise:
    try:
        return await practice.create(req.topic_id, req.type)
    except TopicNotFound:
        raise HTTPException(404, f"Topic '{req.topic_id}' not found") from None
    except GenerationTimeout:
        raise HTTPException(504, "The tutor took too much time. Try again.") from None
    except ProviderConfigError as exc:
        raise HTTPException(503, str(exc)) from None
    except ProviderCallError as exc:
        log.error("LLM provider call failed: %s", exc)
        raise HTTPException(
            503, "The LLM provider refused the request. Check the API key."
        ) from None
    except GenerationError as exc:
        log.warning("Exercise generation failed: %s", exc)
        raise HTTPException(502, "The tutor did not make a valid exercise.") from None


@router.post("/{exercise_id}/answer")
def answer_exercise(exercise_id: str, req: AnswerRequest, practice: Practice) -> Feedback:
    try:
        return practice.answer(exercise_id, req.answer)
    except ExerciseNotFound:
        raise HTTPException(404, f"Exercise '{exercise_id}' not found") from None


topics_router = APIRouter(prefix="/api/topics", tags=["exercises"])


@topics_router.post("/{topic_id}/prefetch", status_code=202)
async def prefetch(topic_id: str, practice: Practice) -> None:
    """Prepare exercises for a topic in the background. The response does not wait."""
    try:
        practice.prefetch(topic_id)
    except TopicNotFound:
        raise HTTPException(404, f"Topic '{topic_id}' not found") from None
