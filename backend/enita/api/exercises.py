"""Exercise endpoints: make an exercise and check an answer."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from enita.agent.clients import ProviderConfigError
from enita.agent.pipeline import GenerationError
from enita.api.topics import get_content
from enita.models import (
    AnswerRequest,
    AttemptFeedback,
    Exercise,
    ExerciseRequest,
    ExplainResponse,
    Solution,
)
from enita.practice.explain import ExplainService
from enita.practice.service import (
    ExerciseClosed,
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


@lru_cache
def get_explainer() -> ExplainService:
    return ExplainService(get_settings(), get_content(), get_db())


Explainer = Annotated[ExplainService, Depends(get_explainer)]


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
async def answer_exercise(
    exercise_id: str, req: AnswerRequest, practice: Practice
) -> AttemptFeedback:
    try:
        return await practice.answer(exercise_id, req.answer)
    except ExerciseNotFound:
        raise HTTPException(404, f"Exercise '{exercise_id}' not found") from None
    except ExerciseClosed:
        raise HTTPException(409, "The exercise is closed. Ask for a new exercise.") from None
    except GenerationTimeout:
        raise HTTPException(504, "The tutor took too much time. Try again.") from None
    except (ProviderConfigError, ProviderCallError) as exc:
        log.error("Grading failed: %s", exc)
        raise HTTPException(
            503, "The LLM provider refused the request. Check the API key."
        ) from None
    except GenerationError as exc:
        log.warning("Grading rejected: %s", exc)
        raise HTTPException(502, "The tutor did not make a valid correction.") from None


@router.post("/{exercise_id}/solution")
def show_solution(exercise_id: str, practice: Practice) -> Solution:
    """Show the model answer and close the exercise."""
    try:
        return practice.solution(exercise_id)
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


@topics_router.post("/{topic_id}/explain")
async def explain(topic_id: str, explainer: Explainer) -> ExplainResponse:
    """'Spiegami meglio': explain the rule again with RAG on the cards."""
    try:
        return await explainer.explain(topic_id)
    except TopicNotFound:
        raise HTTPException(404, f"Topic '{topic_id}' not found") from None
    except GenerationTimeout:
        raise HTTPException(504, "The tutor took too much time. Try again.") from None
    except ProviderConfigError as exc:
        raise HTTPException(503, str(exc)) from None
    except ProviderCallError as exc:
        log.error("Explain failed: %s", exc)
        detail = (
            "The explanation needs OPENAI_API_KEY for the embeddings."
            if "embeddings" in str(exc)
            else "The LLM provider refused the request. Check the API key."
        )
        raise HTTPException(503, detail) from None
    except GenerationError as exc:
        log.warning("Explain rejected: %s", exc)
        raise HTTPException(502, "The tutor did not make a valid explanation.") from None
