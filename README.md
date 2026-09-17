# clawrlos-ops-mcp

A local, self-hosted clone of the `ai-news-mcp` concept — an MCP server that aggregates AI/tech news from 8 sources, caches it in Supabase, and exposes it to any MCP client (Claude Code, Claude Desktop, nanobot, etc.) over stdio.

Unlike the original hosted version, this one has **no LLM summarization or curation step** — it scrapes, caches, and ranks algorithmically. Refresh runs on a background schedule inside the server process itself (every 6 hours by default); there's no external cron.

## Tools

| Tool | Description |
|---|---|
| `get_top_picks(n=10)` | Top N items across all sources, ranked by normalized score + recency decay. |
| `get_trending_news(source=None, limit=50)` | All cached items, optionally filtered by source (e.g. `hackernews`, `lobsters`). |
| `search_today(query, limit=20)` | Keyword search across the last 24h of cached titles/summaries. |
| `get_new_since(timestamp, limit=50)` | Items first seen after a given ISO-8601 timestamp. |
| `get_repo_quickstart(repo)` | Live GitHub API lookup: repo metadata + a quickstart snippet pulled from the README. |
| `get_paper_brief(arxiv_id_or_url)` | Live arXiv lookup: title, authors, abstract, and a code link if mentioned. |
| `check_cache()` | Cache status: last updated, total items, per-source breakdown. |

## Sources (8)

- **HackerNews** — top stories JSON API
- **HuggingFace Spaces Trending** — JSON API
- **Lobsters** — JSON API
- **GeekNews** — HTML scrape
- **Dev.to** — official JSON API, articles tagged `ai`
- **TechCrunch AI** — dedicated AI category RSS feed
- **The Verge AI** — dedicated AI Atom feed
- **arXiv (latest cs.AI papers)** — official Atom API, newest submissions (distinct from `get_paper_brief`, which looks up one specific paper on demand)

This aggregator is scoped to news articles/posts — it intentionally does **not** scrape or store GitHub repos as feed items (an earlier GitHub Trending source was removed for this reason). `get_repo_quickstart` still exists as a separate, on-demand tool for looking up a specific repo mentioned in an article; it just isn't part of the stored feed.

Each source is scraped independently and failures don't cascade: if one source errors out (network issue, blocked request, changed markup), it's logged and skipped, and the rest of the refresh cycle proceeds normally.

> **Reddit was tried and dropped.** Reddit's public `.json` endpoints are blocked by edge bot-detection for most cloud/VPS IPs regardless of User-Agent, and the OAuth alternative requires Reddit API credentials that in practice need going through Reddit's developer approval process — not realistically obtainable for a project like this. See `CLAUDE.md` if you're tempted to re-add it.

## Setup

1. **Create a Supabase project** (see [supabase.com](https://supabase.com)). In its dashboard, go to **Project Settings → API Keys** and note:
   - The **Project URL** — the bare `https://xxxx.supabase.co` (do **not** use the Data API URL that ends in `/rest/v1/` — see [Deployment gotchas](#deployment-gotchas)).
   - The **`service_role` / secret key** (not `anon`/`publishable` — writes and deletes need to bypass RLS).
2. **Apply the schema**: open the Supabase SQL editor and run [`supabase/schema.sql`](supabase/schema.sql).
3. **Configure environment**: copy `.env.example` to `.env` and fill in `SUPABASE_URL` and `SUPABASE_KEY`.
4. **Install**:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -e ".[dev]"
   ```

## Running locally (Claude Code)

```bash
claude mcp add clawrlos-ops-mcp -- /absolute/path/to/clawrlos-ops-mcp/.venv/bin/clawrlos-ops-mcp
```

Use the **absolute path** to the venv's console script — stdio-launched processes don't source your shell rc files, so a bare `clawrlos-ops-mcp` on `$PATH` won't resolve the same way it does interactively.

## Deploying elsewhere (e.g. nanobot on a remote host)

1. Copy the repo to the target host (`git clone` or `rsync`) and install it there the same way as above (`python3 -m venv .venv && .venv/bin/pip install -e .`).
2. Add an MCP server entry to the host's config, e.g. for [nanobot](https://github.com/HKUDS/nanobot) (`~/.nanobot/config.json`):
   ```json
   {
     "tools": {
       "mcpServers": {
         "ai-news": {
           "command": "/absolute/path/to/clawrlos-ops-mcp/.venv/bin/clawrlos-ops-mcp",
           "args": [],
           "env": {
             "SUPABASE_URL": "${SUPABASE_URL}",
             "SUPABASE_KEY": "${SUPABASE_KEY}"
           }
         }
       }
     }
   }
   ```
3. Restart the host process so it picks up the new config.

### Deployment gotchas

Two real issues came up deploying this to a remote host — worth checking first if the server won't start or won't reach Supabase:

- **`~` is not expanded.** `command` is passed straight to `subprocess.Popen`, which doesn't go through a shell — so `~/clawrlos-ops-mcp/...` fails with `FileNotFoundError`. Always use the absolute path (`echo ~` to find it, e.g. `/root/clawrlos-ops-mcp/...`).
- **`SUPABASE_URL` must be the bare project URL**, not the Data API endpoint. Supabase's dashboard "Data API" page shows a URL ending in `/rest/v1/` — if you paste that into `SUPABASE_URL`, the client doubles the path (`.../rest/v1/rest/v1/...`) and every query fails with a PostgREST `PGRST125: Invalid path specified in request URL` error. Use `https://xxxx.supabase.co` only.

## Testing

```bash
.venv/bin/pytest              # unit tests: ranking logic + respx-mocked scraper parsing, no network
.venv/bin/python tests/manual_client_test.py   # live smoke test — needs real Supabase creds in .env
```

## Configuration reference

| Env var | Default | Notes |
|---|---|---|
| `SUPABASE_URL` | — | required; bare project URL |
| `SUPABASE_KEY` | — | required; `service_role` key |
| `REFRESH_INTERVAL_HOURS` | `6` | how often the background scraper runs |
| `RETENTION_HOURS` | `48` | rows older than this are deleted each cycle |
| `HN_TOP_N` | `60` | how many HackerNews top-story ids to fetch |
| `ARXIV_MAX_RESULTS` | `20` | how many newest cs.AI papers to fetch per refresh |
| `USER_AGENT` | `clawrlos-ops-mcp/0.1` | sent on all outbound scraper requests |
| `GITHUB_TOKEN` | unset | optional; raises `get_repo_quickstart`'s GitHub API rate limit from 60/hr to 5000/hr |
| `LOG_LEVEL` | `INFO` | all logging goes to stderr (stdout is the JSON-RPC channel) |
