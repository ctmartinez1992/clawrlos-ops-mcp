import logging
from xml.etree import ElementTree

import httpx

from ..models import NewsItem
from .base import get_with_retry
from .text_utils import clean_summary

log = logging.getLogger(__name__)

FEED_URL = "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _alternate_link(entry: ElementTree.Element) -> str | None:
    for link_el in entry.findall(f"{ATOM_NS}link"):
        if link_el.get("rel") in (None, "alternate"):
            return link_el.get("href")
    return None


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    try:
        resp = await get_with_retry(client, FEED_URL)
        root = ElementTree.fromstring(resp.text)
    except (httpx.HTTPError, ElementTree.ParseError):
        log.warning("theverge: failed to fetch/parse feed")
        return []

    items: list[NewsItem] = []
    for entry in root.iter(f"{ATOM_NS}entry"):
        id_el = entry.find(f"{ATOM_NS}id")
        entry_id = (id_el.text or "").strip() if id_el is not None else None
        if not entry_id:
            continue

        title_el = entry.find(f"{ATOM_NS}title")
        summary_el = entry.find(f"{ATOM_NS}summary")
        author_name_el = entry.find(f"{ATOM_NS}author/{ATOM_NS}name")

        items.append(
            NewsItem(
                source="theverge_ai",
                external_id=entry_id,
                title=(title_el.text or "").strip() if title_el is not None else "",
                url=_alternate_link(entry),
                summary=clean_summary(
                    summary_el.text if summary_el is not None else None
                ),
                author=(author_name_el.text or "").strip()
                if author_name_el is not None
                else None,
            )
        )
    return items
