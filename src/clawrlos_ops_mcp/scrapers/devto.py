import logging

import httpx

from ..models import NewsItem
from .base import get_with_retry
from .text_utils import clean_summary

log = logging.getLogger(__name__)

ARTICLES_URL = "https://dev.to/api/articles"


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    try:
        resp = await get_with_retry(
            client, ARTICLES_URL, params={"tag": "ai", "per_page": 30}
        )
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        log.warning("devto: failed to fetch articles")
        return []

    items: list[NewsItem] = []
    for article in data:
        article_id = article.get("id")
        if article_id is None:
            continue
        user = article.get("user") or {}
        items.append(
            NewsItem(
                source="devto",
                external_id=str(article_id),
                title=article.get("title", ""),
                url=article.get("url"),
                summary=clean_summary(article.get("description")),
                score=article.get("public_reactions_count"),
                author=user.get("username"),
                extra={
                    "tags": article.get("tag_list", []),
                    "comments_count": article.get("comments_count", 0),
                },
            )
        )
    return items
