import logging

import httpx

from ..models import NewsItem
from .base import get_with_retry

log = logging.getLogger(__name__)

SPACES_URL = "https://huggingface.co/api/spaces?sort=trendingScore&limit=50"


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    try:
        resp = await get_with_retry(client, SPACES_URL)
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        log.warning("huggingface: failed to fetch trending spaces")
        return []

    items: list[NewsItem] = []
    for space in data:
        space_id = space.get("id")
        if not space_id:
            continue
        card_data = space.get("cardData") or {}
        title = card_data.get("title") or space_id
        items.append(
            NewsItem(
                source="huggingface_spaces",
                external_id=space_id,
                title=title,
                url=f"https://huggingface.co/spaces/{space_id}",
                score=space.get("trendingScore") or space.get("likes"),
                extra={"likes": space.get("likes")},
            )
        )
    return items
