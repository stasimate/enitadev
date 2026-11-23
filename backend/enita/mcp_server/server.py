"""The Enita MCP server. It gives the theory content to the tutor and to other hosts.

Start it with stdio: `uv run python -m enita.mcp_server`.
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from enita.content.loader import ContentRepository
from enita.settings import get_settings
from enita.storage.db import Database


def build_server(content: ContentRepository | None = None, db: Database | None = None) -> FastMCP:
    repo = content or ContentRepository(get_settings().content_dir)
    store = db or Database(get_settings().db_path)
    server = FastMCP(
        name="enita",
        log_level="WARNING",
        instructions="Theory cards of Enita: English grammar for Italian speakers (CEFR A1-B1).",
    )

    @server.tool()
    def get_theory_card(topic_id: str) -> str:
        """Return the theory card of a topic as markdown.

        The card has the sections Regola, Esempi, Attenzione and Riepilogo.
        The section slugs (regola, esempi, attenzione, riepilogo) are the rule references.
        """
        card = repo.get(topic_id)
        if card is None:
            known = ", ".join(t.id for t in repo.list_topics())
            raise ToolError(f"Unknown topic '{topic_id}'. Known topics: {known}")
        return card.as_markdown()

    @server.tool()
    def get_learner_profile(topic_id: str) -> str:
        """Return the progress of the student on a topic, as JSON.

        It contains aggregates only: attempts, accuracy and the rule references
        (`topic#section`) with the most wrong answers. Use it to practise the weak rules.
        """
        return store.profile(topic_id).model_dump_json()

    return server


def main() -> None:
    build_server().run(transport="stdio")
