import logging
import re

import httpx
from bs4 import BeautifulSoup

from ..models import NewsItem
from .base import get_with_retry

log = logging.getLogger(__name__)

FRONT_PAGE_URL = "https://news.hada.io"
DISCUSSION_URL = "https://news.hada.io/topic?id={id}"


def _parse_score(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"\d+", text)
    return float(match.group()) if match else None


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    try:
        resp = await get_with_retry(client, FRONT_PAGE_URL)
    except httpx.HTTPError:
        log.warning("geeknews: failed to fetch front page")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    items: list[NewsItem] = []

    for row in soup.select("div.topic_row"):
        try:
            topic_id = row.get("data-topic-state-id")
            if not topic_id:
                continue

            title_link = row.select_one("div.topictitle a.topic-title-link")
            if title_link is None:
                continue
            heading = title_link.select_one("h2")
            title = heading.get_text(strip=True) if heading else ""

            href = title_link.get("href", "")
            url = href if href.startswith("http") else DISCUSSION_URL.format(id=topic_id)

            desc_link = row.select_one("div.topicdesc a")
            summary = desc_link.get_text(strip=True) if desc_link else None

            score_el = row.select_one(f"span#tp{topic_id}")
            score = _parse_score(score_el.get_text() if score_el else None)

            author_link = row.select_one("div.topicinfo a[href^='/@']")
            author = author_link.get_text(strip=True) if author_link else None

            time_el = row.select_one("time.js-relative-time")
            published_at = time_el.get("datetime") if time_el else None

            items.append(
                NewsItem(
                    source="geeknews",
                    external_id=str(topic_id),
                    title=title,
                    url=url,
                    summary=summary,
                    score=score,
                    author=author,
                    extra={"published_at": published_at},
                )
            )
        except Exception:
            log.warning("geeknews: failed to parse a row", exc_info=True)
            continue

    return items
