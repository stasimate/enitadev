"""Learner endpoints: the progress (permanent memory) and the audit trail."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from enita.api.exercises import Practice, get_db
from enita.models import LearnerProfile
from enita.storage.db import Database

router = APIRouter(prefix="/api", tags=["learner"])


@router.get("/progress")
def progress(practice: Practice, topic_id: str | None = None) -> LearnerProfile:
    return practice.profile(topic_id)


@router.get("/audit")
def audit(
    db: Annotated[Database, Depends(get_db)], limit: Annotated[int, Query(ge=1, le=200)] = 20
) -> list[dict[str, Any]]:
    """The most recent audit records: exercise generations, corrections, guardrail events."""
    return db.list_audit(limit)
