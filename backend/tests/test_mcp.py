"""The MCP server over stdio, with the same client that the tutor uses."""

from enita.practice.service import mcp_tools
from enita.settings import get_settings


async def test_mcp_server_gives_theory_tool() -> None:
    async with mcp_tools(get_settings())() as tools:
        assert sorted(t.name for t in tools) == [
            "get_learner_profile",
            "get_theory_card",
            "search_grammar",
        ]


async def test_get_theory_card_over_stdio() -> None:
    import os
    import sys

    from datapizza.tools.mcp_client import MCPClient

    env = {"PATH": os.environ.get("PATH", "")}
    async with MCPClient(command=sys.executable, args=["-m", "enita.mcp_server"], env=env) as c:
        ok = await c.call_tool("get_theory_card", {"topic_id": "present-simple"})
        bad = await c.call_tool("get_theory_card", {"topic_id": "nope"})
    assert not ok.isError and "## Regola" in ok.content[0].text
    assert bad.isError and "Unknown topic" in bad.content[0].text
