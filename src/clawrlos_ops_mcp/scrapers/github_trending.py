import logging
import re

import httpx
from bs4 import BeautifulSoup

from ..models import NewsItem
from .base import get_with_retry

log = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending"


def _parse_stars(text: str) -> float | None:
    text = text.strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    try:
        resp = await get_with_retry(client, TRENDING_URL)
    except httpx.HTTPError:
        log.warning("github_trending: failed to fetch trending page")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    items: list[NewsItem] = []

    for row in soup.select("article.Box-row"):
        try:
            heading = row.select_one("h2 a")
            if heading is None:
                continue
            repo = "/".join(
                part.strip() for part in heading.get_text().split("/") if part.strip()
            )
            if not repo:
                continue
            href = heading.get("href", "").strip()
            url = f"https://github.com{href}" if href else None

            desc_el = row.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else None

            stars_el = row.select_one('a[href$="/stargazers"]')
            stars = _parse_stars(stars_el.get_text()) if stars_el else None

            lang_el = row.select_one('span[itemprop="programmingLanguage"]')
            language = lang_el.get_text(strip=True) if lang_el else None

            stars_today_el = row.select_one("span.d-inline-block.float-sm-right")
            stars_today_text = (
                stars_today_el.get_text(strip=True) if stars_today_el else None
            )
            stars_today_match = (
                re.search(r"[\d,]+", stars_today_text) if stars_today_text else None
            )
            stars_today = (
                _parse_stars(stars_today_match.group()) if stars_today_match else None
            )

            items.append(
                NewsItem(
                    source="github_trending",
                    external_id=repo,
                    title=repo,
                    url=url,
                    summary=description,
                    score=stars,
                    extra={"language": language, "stars_today": stars_today},
                )
            )
        except Exception:
            log.warning("github_trending: failed to parse a row", exc_info=True)
            continue

    return items
