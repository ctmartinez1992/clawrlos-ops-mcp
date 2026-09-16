from collections.abc import Awaitable, Callable

import httpx

from ..models import NewsItem
from . import geeknews, github_trending, hackernews, huggingface, lobsters, reddit

Scraper = Callable[[httpx.AsyncClient], Awaitable[list[NewsItem]]]

REDDIT_SUBREDDITS = [
    "ClaudeAI",
    "vibecoding",
    "codex",
    "claudecode",
    "openclaw",
    "artificial",
    "ArtificialInteligence",
]


def _reddit_scraper(subreddit: str) -> Scraper:
    async def _fetch(client: httpx.AsyncClient) -> list[NewsItem]:
        return await reddit.fetch_subreddit(client, subreddit)

    return _fetch


ALL_SCRAPERS: list[Scraper] = [
    hackernews.fetch,
    *[_reddit_scraper(sub) for sub in REDDIT_SUBREDDITS],
    github_trending.fetch,
    huggingface.fetch,
    lobsters.fetch,
    geeknews.fetch,
]
