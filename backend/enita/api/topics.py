"""Topic endpoints: the list of topics and the theory card of one topic."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from enita.content.loader import ContentRepository
from enita.models import TopicCard, TopicSummary
from enita.settings import get_settings

router = APIRouter(prefix="/api/topics", tags=["topics"])


@lru_cache
def get_content() -> ContentRepository:
    return ContentRepository(get_settings().content_dir)


Content = Annotated[ContentRepository, Depends(get_content)]


@router.get("")
def list_topics(content: Content) -> list[TopicSummary]:
    return content.list_topics()


@router.get("/{topic_id}")
def get_topic(topic_id: str, content: Content) -> TopicCard:
    card = content.get(topic_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
    return card
