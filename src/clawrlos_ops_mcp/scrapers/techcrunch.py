import logging
from xml.etree import ElementTree

import httpx

from ..models import NewsItem
from .base import get_with_retry
from .text_utils import clean_summary

log = logging.getLogger(__name__)

FEED_URL = "https://techcrunch.com/category/artificial-intelligence/feed/"
DC_NS = "{http://purl.org/dc/elements/1.1/}"


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    try:
        resp = await get_with_retry(client, FEED_URL)
        root = ElementTree.fromstring(resp.text)
    except (httpx.HTTPError, ElementTree.ParseError):
        log.warning("techcrunch: failed to fetch/parse feed")
        return []

    items: list[NewsItem] = []
    for entry in root.iter("item"):
        guid_el = entry.find("guid")
        guid = (guid_el.text or "").strip() if guid_el is not None else ""
        if not guid:
            continue

        title_el = entry.find("title")
        link_el = entry.find("link")
        description_el = entry.find("description")
        creator_el = entry.find(f"{DC_NS}creator")

        items.append(
            NewsItem(
                source="techcrunch_ai",
                external_id=guid,
                title=(title_el.text or "").strip() if title_el is not None else "",
                url=(link_el.text or "").strip() if link_el is not None else None,
                summary=clean_summary(
                    description_el.text if description_el is not None else None
                ),
                author=(creator_el.text or "").strip() if creator_el is not None else None,
            )
        )
    return items
