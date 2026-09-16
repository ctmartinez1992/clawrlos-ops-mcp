import logging

import httpx

from ..models import NewsItem
from .base import get_with_retry

log = logging.getLogger(__name__)

HOTTEST_URL = "https://lobste.rs/hottest.json"
SUMMARY_MAX_LEN = 280


def _clean_summary(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = " ".join(text.split())
    if not cleaned:
        return None
    if len(cleaned) > SUMMARY_MAX_LEN:
        return cleaned[:SUMMARY_MAX_LEN] + "..."
    return cleaned


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    try:
        resp = await get_with_retry(client, HOTTEST_URL)
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        log.warning("lobsters: failed to fetch hottest")
        return []

    items: list[NewsItem] = []
    for story in data:
        short_id = story.get("short_id")
        if not short_id:
            continue
        # submitter_user is a plain username string, not an object.
        author = story.get("submitter_user")
        items.append(
            NewsItem(
                source="lobsters",
                external_id=short_id,
                title=story.get("title", ""),
                url=story.get("url") or story.get("comments_url"),
                summary=_clean_summary(story.get("description_plain")),
                score=story.get("score"),
                author=author if isinstance(author, str) else None,
                extra={"comment_count": story.get("comment_count", 0)},
            )
        )
    return items
