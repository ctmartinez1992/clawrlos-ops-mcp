import logging

import httpx

from ..config import settings
from ..models import NewsItem
from .base import get_with_retry

log = logging.getLogger(__name__)

SUBREDDIT_URL = "https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
SUMMARY_MAX_LEN = 280


async def fetch_subreddit(
    client: httpx.AsyncClient, subreddit: str
) -> list[NewsItem]:
    url = SUBREDDIT_URL.format(subreddit=subreddit, limit=settings.reddit_limit)
    try:
        resp = await get_with_retry(client, url)
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        log.warning("reddit: failed to fetch r/%s", subreddit)
        return []

    children = data.get("data", {}).get("children", [])
    source = f"reddit_{subreddit.lower()}"
    items: list[NewsItem] = []

    for child in children:
        post = child.get("data", {})
        permalink = post.get("permalink")
        reddit_url = f"https://www.reddit.com{permalink}" if permalink else None
        external_url = post.get("url")

        selftext = post.get("selftext") or ""
        summary = None
        if selftext:
            summary = selftext[:SUMMARY_MAX_LEN]
            if len(selftext) > SUMMARY_MAX_LEN:
                summary += "..."

        items.append(
            NewsItem(
                source=source,
                external_id=post.get("name", ""),
                title=post.get("title", ""),
                url=reddit_url,
                summary=summary,
                score=post.get("score") or post.get("ups"),
                author=post.get("author"),
                extra={
                    "num_comments": post.get("num_comments", 0),
                    "external_url": external_url
                    if external_url and external_url != reddit_url
                    else None,
                },
            )
        )

    return [item for item in items if item.external_id]
