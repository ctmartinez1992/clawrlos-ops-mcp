from collections.abc import Awaitable, Callable

import httpx

from ..models import NewsItem
from . import geeknews, hackernews, huggingface, lobsters

Scraper = Callable[[httpx.AsyncClient], Awaitable[list[NewsItem]]]

ALL_SCRAPERS: list[Scraper] = [
    hackernews.fetch,
    huggingface.fetch,
    lobsters.fetch,
    geeknews.fetch,
]
