# clawrlos-ops-mcp

A local Python MCP server (stdio transport, built on `mcp[cli]`'s `FastMCP`) that scrapes 8 AI/tech news sources, caches results in Supabase, and exposes 7 read tools. No LLM summarization or curation — ranking is a pure algorithmic function. This is scoped to news articles/posts only — it does not scrape or store GitHub repos as feed items (see "Known external constraints" below); `get_repo_quickstart` is a separate on-demand lookup tool, not part of the stored feed. See `README.md` for setup/usage; this file is about working on the code itself.

## Architecture

```
server.py       FastMCP instance, lifespan (opens SupabaseStore, starts the
                background refresh task), @mcp.tool() registrations
scheduler.py    refresh_loop(): asyncio sleep-loop, re-scrapes every
                REFRESH_INTERVAL_HOURS, then deletes rows older than
                RETENTION_HOURS
scrapers/       one fetch(client) -> list[NewsItem] per source, registered
                in scrapers/__init__.py:ALL_SCRAPERS
enrich/         live (non-cached) lookups for get_repo_quickstart (GitHub
                API) and get_paper_brief (arXiv API)
db.py           SupabaseStore — every method is async, wrapping the
                synchronous supabase-py client via asyncio.to_thread
ranking.py      pure function: normalizes scores per-source, applies a
                recency decay, caps items per source — used by
                get_top_picks
config.py       pydantic-settings Settings, read from .env / real env vars
```

## Conventions to follow

- **Scrapers must never raise.** `scheduler.py` runs all of `ALL_SCRAPERS` via `asyncio.gather(..., return_exceptions=True)` and depends on each `fetch()` catching its own `httpx.HTTPError`/parse errors, logging a warning, and returning `[]` (or partial results) instead of propagating. One broken source must not break the refresh cycle for the other 7.
- **Logging goes to stderr only.** This is a stdio MCP server — stdout is the JSON-RPC channel. `server.py` configures `logging.basicConfig(stream=sys.stderr, ...)` at import time; never add a `print()` or a stdout handler anywhere in this codebase.
- **`supabase-py`'s client is synchronous.** Any new `SupabaseStore` method must wrap its Supabase call in `asyncio.to_thread(...)`, same as the existing methods in `db.py` — otherwise a blocking network call stalls the whole event loop and every concurrent tool call.
- **New scraper checklist**: add `scrapers/<name>.py` with `async def fetch(client: httpx.AsyncClient) -> list[NewsItem]`, register it in `scrapers/__init__.py:ALL_SCRAPERS`, pick a stable `source` label and `external_id` (used in Supabase's `unique(source, external_id)` upsert key), and add a respx-mocked test + fixture in `tests/` mirroring the existing ones. If the source has a free-text summary/description, run it through `scrapers/text_utils.py:clean_summary()` (used by `lobsters.py`, `devto.py`, `techcrunch.py`, and `theverge.py`) instead of writing another whitespace-collapse/truncate helper. This aggregator is scoped to news articles/posts — don't add a scraper that stores repos, packages, or other non-article entities as feed items (see the GitHub Trending removal below); a live-lookup tool under `enrich/` is the right place for that kind of data instead.
- **HTML scrapers are brittle by nature.** `geeknews.py` parses live page markup with BeautifulSoup; it already does per-row try/except with skip-and-log rather than a page-level try/except, so a single malformed row doesn't drop the whole source. If the site changes its markup, tests will still pass (fixtures are frozen snapshots) but live scraping may return `0` items — check `check_cache()`'s per-source breakdown after a deploy if a source looks unexpectedly empty.

## Dependency pin: keep `mcp[cli]<2`

`pyproject.toml` pins `mcp[cli]>=1.30.0,<2` deliberately. `mcp` v2.x renamed `FastMCP` → `MCPServer` and changed the surrounding API; this codebase is built against v1's `FastMCP` / `Context` / `lifespan` pattern (see `server.py`). Don't bump past `<2` without rewriting `server.py` against the new API.

## Known external constraints (not code bugs)

- **Do not re-add Reddit/subreddits as a news source — it was tried twice and doesn't work.** First attempt: scrape Reddit's public `.json` endpoints directly. Confirmed by direct testing that this is blocked at Reddit's edge/WAF, not by anything in this code — `www.reddit.com/r/<sub>/hot.json` returns `HTTP 403` with a ~190KB HTML interstitial regardless of `User-Agent`; `old.reddit.com/r/<sub>/hot.json` `302`-redirects logged-out requests to a login wall; and even `oauth.reddit.com/r/<sub>/hot` with **no token at all** returns the byte-identical 190KB 403 page, meaning the block happens before any app-layer auth check, for every reddit.com host tried, from this network. Second attempt: switch to Reddit's official OAuth API (`client_credentials` grant). Abandoned before shipping because getting real Reddit API credentials in practice requires going through Reddit's developer approval process, which isn't realistically available for a personal/small project like this one — so there was no way to obtain or verify a working `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`. Both attempts were fully removed from the codebase; there is no reddit scraper, config, or test left to build on.
- **GeekNews** is HTML-scraped against an unversioned page — the source most likely to need selector updates if the site redesigns. (GitHub Trending was removed entirely — see the project summary at the top of this file — so GeekNews is now the only HTML-scraped source.)
- **TechCrunch AI, The Verge AI, and arXiv** are all fetched as RSS/Atom XML (`xml.etree.ElementTree`, stdlib, same approach as `enrich/arxiv.py`), not scraped HTML — they're less brittle than GeekNews, but are still third-party feed URLs and shapes a publisher could change or move without notice. None of these three (nor Dev.to) have a native "score" field; `ranking.py` already degrades gracefully for scoreless sources (see `rank()`'s `hi > 0` check), so items from these four sources rank by recency alone within their own source group.

## Deployment gotchas

Learned the hard way running this under `nanobot` on a remote host — relevant to anyone editing an MCP client's config to point at this server:
- Config values are passed straight to `subprocess.Popen`, not through a shell, so `~` is never expanded. Always use an absolute path for `command`.
- `SUPABASE_URL` must be the bare project URL (`https://xxxx.supabase.co`). Pasting Supabase's Data API URL (which ends in `/rest/v1/`) doubles the request path and every query fails with PostgREST's `PGRST125`.

## Testing

```bash
.venv/bin/pytest                                 # unit tests, no network (ranking + respx-mocked scrapers)
.venv/bin/python tests/manual_client_test.py     # live stdio smoke test — needs real Supabase creds in .env
```

`mcp dev` / `mcp run` shell out to `uv`, which may not be installed — `manual_client_test.py` talks to the server directly via `mcp.client.stdio.stdio_client` + `ClientSession` instead, so it has no `uv` dependency.
