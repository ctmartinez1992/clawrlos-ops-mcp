import asyncio
import contextlib
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from mcp.server.fastmcp import Context, FastMCP

from .config import settings
from .db import SupabaseStore
from .enrich.arxiv import get_paper_brief as _get_paper_brief
from .enrich.github import get_repo_quickstart as _get_repo_quickstart
from .models import NewsItem
from .ranking import rank
from .scheduler import refresh_loop

logging.basicConfig(
    stream=sys.stderr,
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@dataclass
class AppContext:
    db: SupabaseStore


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    db = SupabaseStore(settings.supabase_url, settings.supabase_key)
    refresh_task = asyncio.create_task(refresh_loop(db))
    try:
        yield AppContext(db=db)
    finally:
        refresh_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await refresh_task


mcp = FastMCP("clawrlos-ops-mcp", lifespan=app_lifespan)


def _row_to_item(row: dict) -> NewsItem:
    return NewsItem(**{k: row.get(k) for k in NewsItem.model_fields})


@mcp.tool()
async def get_top_picks(n: int = 10, ctx: Context = None) -> list[NewsItem]:
    """Top N news items ranked across all sources by normalized score + recency."""
    db: SupabaseStore = ctx.request_context.lifespan_context.db
    rows = await db.fetch_recent(hours=settings.retention_hours, limit=1000)
    ranked = rank(rows)
    return [_row_to_item(row) for row in ranked[:n]]


@mcp.tool()
async def get_trending_news(
    source: str | None = None, limit: int = 50, ctx: Context = None
) -> list[NewsItem]:
    """All cached news, optionally filtered by source (e.g. reddit_claudeai, hackernews)."""
    db: SupabaseStore = ctx.request_context.lifespan_context.db
    rows = await db.fetch_recent(
        hours=settings.retention_hours, source=source, limit=limit
    )
    return [_row_to_item(row) for row in rows]


@mcp.tool()
async def search_today(query: str, limit: int = 20, ctx: Context = None) -> list[NewsItem]:
    """Keyword search across today's cached titles and summaries."""
    db: SupabaseStore = ctx.request_context.lifespan_context.db
    rows = await db.fetch_recent(hours=24, limit=1000)
    needle = query.lower()
    matches = [
        row
        for row in rows
        if needle in (row.get("title") or "").lower()
        or needle in (row.get("summary") or "").lower()
    ]
    return [_row_to_item(row) for row in matches[:limit]]


@mcp.tool()
async def get_new_since(
    timestamp: str, limit: int = 50, ctx: Context = None
) -> list[NewsItem]:
    """Items added after the given ISO-8601 timestamp."""
    try:
        since = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp: {timestamp!r}") from exc

    db: SupabaseStore = ctx.request_context.lifespan_context.db
    rows = await db.fetch_since(since, limit=limit)
    return [_row_to_item(row) for row in rows]


@mcp.tool()
async def get_repo_quickstart(repo: str) -> dict:
    """GitHub repo metadata (stars, language, topics) + a quickstart snippet from its README."""
    return await _get_repo_quickstart(repo)


@mcp.tool()
async def get_paper_brief(arxiv_id_or_url: str) -> dict:
    """ArXiv paper title, authors, abstract, and code repo link if available."""
    return await _get_paper_brief(arxiv_id_or_url)


@mcp.tool()
async def check_cache(ctx: Context = None) -> dict:
    """Cache status: last updated, total items, per-source breakdown."""
    db: SupabaseStore = ctx.request_context.lifespan_context.db
    return await db.cache_stats()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
