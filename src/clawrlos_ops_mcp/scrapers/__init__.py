from collections.abc import Awaitable, Callable

import httpx

from ..models import NewsItem
from . import (
    arxiv_news,
    devto,
    geeknews,
    hackernews,
    huggingface,
    lobsters,
    techcrunch,
    theverge,
)

Scraper = Callable[[httpx.AsyncClient], Awaitable[list[NewsItem]]]

ALL_SCRAPERS: list[Scraper] = [
    hackernews.fetch,
    huggingface.fetch,
    lobsters.fetch,
    geeknews.fetch,
    devto.fetch,
    techcrunch.fetch,
    theverge.fetch,
    arxiv_news.fetch,
]
