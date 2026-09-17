from pathlib import Path

import httpx
import pytest
import respx

from clawrlos_ops_mcp.scrapers import (
    arxiv_news,
    devto,
    geeknews,
    hackernews,
    huggingface,
    lobsters,
    techcrunch,
    theverge,
)

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


@pytest.mark.asyncio
@respx.mock
async def test_devto_fetch_parses_articles():
    respx.get(url__regex=r"https://dev\.to/api/articles.*").mock(
        return_value=httpx.Response(200, text=_read("devto_articles.json"))
    )

    async with httpx.AsyncClient() as client:
        items = await devto.fetch(client)

    assert len(items) == 2
    assert items[0].source == "devto"
    assert items[0].external_id == "4669106"
    assert items[0].author == "exampleuser"
    assert items[0].score == 42
    assert items[0].extra["tags"] == ["ai", "machinelearning"]
    assert items[1].summary is None


@pytest.mark.asyncio
@respx.mock
async def test_techcrunch_fetch_parses_items():
    respx.get("https://techcrunch.com/category/artificial-intelligence/feed/").mock(
        return_value=httpx.Response(200, text=_read("techcrunch_feed.xml"))
    )

    async with httpx.AsyncClient() as client:
        items = await techcrunch.fetch(client)

    assert len(items) == 2
    assert items[0].source == "techcrunch_ai"
    assert items[0].external_id == "https://techcrunch.com/?p=3164745"
    assert items[0].title == "Example AI startup raises a big round"
    assert items[0].author == "Jane Reporter"
    assert items[0].summary == "A short teaser about the funding round."
    assert items[1].summary is None


@pytest.mark.asyncio
@respx.mock
async def test_theverge_fetch_parses_entries():
    respx.get("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml").mock(
        return_value=httpx.Response(200, text=_read("theverge_feed.xml"))
    )

    async with httpx.AsyncClient() as client:
        items = await theverge.fetch(client)

    assert len(items) == 2
    assert items[0].source == "theverge_ai"
    assert items[0].external_id == "https://www.theverge.com/?p=996234"
    assert (
        items[0].url
        == "https://www.theverge.com/ai-artificial-intelligence/996234/example-ai-feature-ships-today"
    )
    assert items[0].author == "Stevie Bonifield"
    assert items[0].summary == "A short summary of the new AI feature."


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_news_fetch_parses_entries():
    respx.get(url__regex=r"https://export\.arxiv\.org/api/query.*").mock(
        return_value=httpx.Response(200, text=_read("arxiv_ai_feed.xml"))
    )

    async with httpx.AsyncClient() as client:
        items = await arxiv_news.fetch(client)

    assert len(items) == 2
    assert items[0].source == "arxiv_ai"
    assert items[0].external_id == "2609.17527v1"
    assert items[0].url == "https://arxiv.org/abs/2609.17527v1"
    assert items[0].author == "Tapan Chugh, Vidushi Singh, Krish Jain, et al."
    assert items[0].extra["categories"] == ["cs.MA", "cs.AI"]

    second = items[1]
    assert second.external_id == "2609.17600v2"
    assert second.author == "Solo Author"
