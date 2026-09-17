import logging
import re
from xml.etree import ElementTree

import httpx

from ..config import settings
from ..models import NewsItem
from .base import get_with_retry
from .text_utils import clean_summary

log = logging.getLogger(__name__)

QUERY_URL = (
    "https://export.arxiv.org/api/query"
    "?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending"
    "&max_results={max_results}"
)
ATOM_NS = "{http://www.w3.org/2005/Atom}"
MAX_AUTHORS = 3


def _extract_arxiv_id(id_url: str) -> str | None:
    match = re.search(r"arxiv\.org/abs/([\w.\-]+)$", id_url)
    return match.group(1) if match else None


def _authors(entry: ElementTree.Element) -> str | None:
    names = [
        (name_el.text or "").strip()
        for author in entry.findall(f"{ATOM_NS}author")
        if (name_el := author.find(f"{ATOM_NS}name")) is not None and name_el.text
    ]
    if not names:
        return None
    if len(names) > MAX_AUTHORS:
        return ", ".join(names[:MAX_AUTHORS]) + ", et al."
    return ", ".join(names)


async def fetch(client: httpx.AsyncClient) -> list[NewsItem]:
    url = QUERY_URL.format(max_results=settings.arxiv_max_results)
    try:
        resp = await get_with_retry(client, url)
        root = ElementTree.fromstring(resp.text)
    except (httpx.HTTPError, ElementTree.ParseError):
        log.warning("arxiv_news: failed to fetch/parse feed")
        return []

    items: list[NewsItem] = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        id_el = entry.find(f"{ATOM_NS}id")
        raw_id = (id_el.text or "").strip() if id_el is not None else ""
        arxiv_id = _extract_arxiv_id(raw_id) if raw_id else None
        if not arxiv_id:
            continue

        title_el = entry.find(f"{ATOM_NS}title")
        summary_el = entry.find(f"{ATOM_NS}summary")
        categories = [
            cat_el.get("term")
            for cat_el in entry.findall(f"{ATOM_NS}category")
            if cat_el.get("term")
        ]

        items.append(
            NewsItem(
                source="arxiv_ai",
                external_id=arxiv_id,
                title=(title_el.text or "").strip().replace("\n", " ")
                if title_el is not None
                else "",
                url=f"https://arxiv.org/abs/{arxiv_id}",
                summary=clean_summary(
                    summary_el.text if summary_el is not None else None
                ),
                author=_authors(entry),
                extra={"categories": categories},
            )
        )
    return items
