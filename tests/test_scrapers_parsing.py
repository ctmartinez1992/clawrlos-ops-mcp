from pathlib import Path

import httpx
import pytest
import respx

from clawrlos_ops_mcp.scrapers import geeknews, github_trending, hackernews, huggingface, lobsters
from clawrlos_ops_mcp.scrapers.reddit import fetch_subreddit

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.mark.asyncio
@respx.mock
async def test_hackernews_fetch_parses_stories():
    respx.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
        return_value=httpx.Response(200, text=_read("hackernews_topstories.json"))
    )
    respx.get("https://hacker-news.firebaseio.com/v0/item/111.json").mock(
        return_value=httpx.Response(200, text=_read("hackernews_item_111.json"))
    )
    respx.get("https://hacker-news.firebaseio.com/v0/item/222.json").mock(
        return_value=httpx.Response(200, text=_read("hackernews_item_222.json"))
    )

    async with httpx.AsyncClient() as client:
        items = await hackernews.fetch(client)

    assert len(items) == 2
    by_id = {i.external_id: i for i in items}
    assert by_id["111"].title == "A cool AI project"
    assert by_id["111"].url == "https://example.com/cool-ai-project"
    assert by_id["222"].url == "https://news.ycombinator.com/item?id=222"


@pytest.mark.asyncio
@respx.mock
async def test_reddit_fetch_subreddit_parses_and_truncates_selftext():
    respx.get(url__regex=r"https://www\.reddit\.com/r/ClaudeAI/hot\.json.*").mock(
        return_value=httpx.Response(200, text=_read("reddit_hot.json"))
    )

    async with httpx.AsyncClient() as client:
        items = await fetch_subreddit(client, "ClaudeAI")

    assert len(items) == 2
    assert items[0].source == "reddit_claudeai"
    assert items[0].external_id == "t3_abc123"
    assert items[0].summary is None

    long_post = next(i for i in items if i.external_id == "t3_def456")
    assert long_post.summary is not None
    assert len(long_post.summary) == 283  # 280 chars + "..."
    assert long_post.summary.endswith("...")


@pytest.mark.asyncio
@respx.mock
async def test_github_trending_parses_rows():
    respx.get("https://github.com/trending").mock(
        return_value=httpx.Response(200, text=_read("github_trending.html"))
    )

    async with httpx.AsyncClient() as client:
        items = await github_trending.fetch(client)

    assert len(items) == 2
    first = items[0]
    assert first.external_id == "alibaba/open-code-review"
    assert first.url == "https://github.com/alibaba/open-code-review"
    assert first.score == 30036
    assert first.extra["language"] == "Go"
    assert first.extra["stars_today"] == 2756

    second = items[1]
    assert second.external_id == "example-org/tiny-repo"
    assert second.score == 12


@pytest.mark.asyncio
@respx.mock
async def test_huggingface_fetch_parses_spaces():
    respx.get(url__regex=r"https://huggingface\.co/api/spaces.*").mock(
        return_value=httpx.Response(200, text=_read("huggingface_spaces.json"))
    )

    async with httpx.AsyncClient() as client:
        items = await huggingface.fetch(client)

    assert len(items) == 2
    assert items[0].title == "Cool Space Demo"
    assert items[0].url == "https://huggingface.co/spaces/example-org/cool-space"
    assert items[0].score == 42.5
    assert items[1].score == 3  # falls back to likes when trendingScore missing


@pytest.mark.asyncio
@respx.mock
async def test_lobsters_fetch_parses_stories():
    respx.get("https://lobste.rs/hottest.json").mock(
        return_value=httpx.Response(200, text=_read("lobsters_hottest.json"))
    )

    async with httpx.AsyncClient() as client:
        items = await lobsters.fetch(client)

    assert len(items) == 2
    assert items[0].summary == "Some HTML description."
    assert items[0].author == "erin"
    assert items[1].summary is None


@pytest.mark.asyncio
@respx.mock
async def test_geeknews_fetch_parses_rows():
    respx.get("https://news.hada.io").mock(
        return_value=httpx.Response(200, text=_read("geeknews.html"))
    )

    async with httpx.AsyncClient() as client:
        items = await geeknews.fetch(client)

    assert len(items) == 2
    assert items[0].external_id == "33735"
    assert items[0].url == "https://zanlib.dev/blog/do-you-still-read-the-code/"
    assert items[0].score == 17
    assert items[0].author == "GN⁺"

    second = items[1]
    assert second.url == "https://news.hada.io/topic?id=33762"
