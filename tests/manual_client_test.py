"""Manual stdio smoke test for the clawrlos-ops-mcp server.

Not a pytest test (it needs a live Supabase project configured via .env
and makes real network calls). Run directly:

    python tests/manual_client_test.py

It starts the server as a subprocess over stdio, lists all tools, and
calls each one once, printing the results.
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "clawrlos_ops_mcp.server"],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print(f"Tools available ({len(names)}): {names}")

            print("\n--- check_cache ---")
            result = await session.call_tool("check_cache", {})
            print(result.content)

            print("\n--- get_top_picks(n=5) ---")
            result = await session.call_tool("get_top_picks", {"n": 5})
            print(result.content)

            print("\n--- get_trending_news(limit=5) ---")
            result = await session.call_tool("get_trending_news", {"limit": 5})
            print(result.content)

            print("\n--- search_today(query='ai') ---")
            result = await session.call_tool("search_today", {"query": "ai"})
            print(result.content)

            print("\n--- get_new_since(1h ago) ---")
            from datetime import datetime, timedelta, timezone

            since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            result = await session.call_tool("get_new_since", {"timestamp": since})
            print(result.content)

            print("\n--- get_repo_quickstart('modelcontextprotocol/python-sdk') ---")
            result = await session.call_tool(
                "get_repo_quickstart", {"repo": "modelcontextprotocol/python-sdk"}
            )
            print(result.content)

            print("\n--- get_paper_brief('1706.03762') ---")
            result = await session.call_tool(
                "get_paper_brief", {"arxiv_id_or_url": "1706.03762"}
            )
            print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
