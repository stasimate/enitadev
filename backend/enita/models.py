"""Pydantic schemas that the API, the agent and the MCP server share."""

from typing import Literal

from pydantic import BaseModel

Level = Literal["A1", "A2", "B1"]

SECTION_SLUGS: tuple[str, ...] = ("regola", "esempi", "attenzione", "riepilogo")


class TopicSummary(BaseModel):
    id: str
    title: str
    level: Level
    tags: list[str] = []


class Section(BaseModel):
    slug: str
    title: str
    markdown: str


class TopicCard(TopicSummary):
    sections: list[Section]

    def has_section(self, slug: str) -> bool:
        return any(s.slug == slug for s in self.sections)
