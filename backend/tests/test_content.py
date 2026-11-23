from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enita.content.loader import ContentError, ContentRepository, parse_card
from enita.main import app
from enita.settings import get_settings

VALID = """---
id: demo
title: Demo
level: A2
tags: [x]
---

## Regola
R

## Esempi
E

## Attenzione
A

## Riepilogo
S
"""


def test_parse_valid_card() -> None:
    card = parse_card(VALID)
    assert card.id == "demo"
    assert [s.slug for s in card.sections] == ["regola", "esempi", "attenzione", "riepilogo"]
    assert card.sections[0].markdown == "R"


@pytest.mark.parametrize(
    "text",
    [
        VALID.replace("---\nid", "id", 1),  # no front matter
        VALID.replace("## Esempi", "## Examples"),  # wrong section
        VALID.replace("level: A2", "level: C2"),  # level not allowed
    ],
)
def test_parse_invalid_card(text: str) -> None:
    with pytest.raises(ContentError):
        parse_card(text)


def test_all_repo_cards_are_valid() -> None:
    repo = ContentRepository(get_settings().content_dir)
    topics = repo.list_topics()
    assert topics, "there must be at least one card"
    assert repo.rule_ref_exists(f"{topics[0].id}#regola")
    assert not repo.rule_ref_exists(f"{topics[0].id}#missing")


def test_id_must_match_filename(tmp_path: Path) -> None:
    (tmp_path / "other.md").write_text(VALID, encoding="utf-8")
    with pytest.raises(ContentError):
        ContentRepository(tmp_path).list_topics()


def test_topics_api() -> None:
    client = TestClient(app)
    listing = client.get("/api/topics").json()
    assert any(t["id"] == "present-simple" for t in listing)
    card = client.get("/api/topics/present-simple").json()
    assert card["level"] == "A1" and len(card["sections"]) == 4
    assert client.get("/api/topics/nope").status_code == 404
