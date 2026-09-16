import asyncio
import logging

import httpx

from ..config import settings
from ..models import NewsItem
from .base import get_with_retry

log = logging.getLogger(__name__)

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
DISCUSSION_URL = "https://news.ycombinator.com/item?id={id}"

_SEMAPHORE_LIMIT = 10


async def _fetch_item(
    client: httpx.AsyncClient, item_id: int, sem: asyncio.Semaphore
) -> NewsItem | None:
    async with sem:
        try:
            resp = await get_with_retry(client, ITEM_URL.format(id=item_id))
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            log.warning("hackernews: failed to fetch item %s", item_id)
            return None

    if not data or data.get("type") != "story":
        return None

    return NewsItem(
        source="hackernews",
        external_id=str(item_id),
        title=data.get("title", ""),
        url=data.get("url") or DISCUSSION_URL.format(id=item_id),
        score=data.get("score"),
        author=data.get("by"),
        extra={"num_comments": data.get("descendants", 0)},
    )


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    resp = await get_with_retry(client, TOP_STORIES_URL)
    ids = resp.json()[: settings.hn_top_n]

    sem = asyncio.Semaphore(_SEMAPHORE_LIMIT)
    results = await asyncio.gather(*(_fetch_item(client, i, sem) for i in ids))
    return [item for item in results if item is not None]
