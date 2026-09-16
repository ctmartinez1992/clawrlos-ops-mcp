import asyncio
from datetime import datetime, timedelta, timezone

from supabase import Client, create_client

from .models import NewsItem

TABLE = "news_items"


class SupabaseStore:
    def __init__(self, url: str, key: str) -> None:
        self._client: Client = create_client(url, key)

    async def upsert_items(self, items: list[NewsItem]) -> int:
        if not items:
            return 0
        rows = [
            {
                "source": item.source,
                "external_id": item.external_id,
                "title": item.title,
                "url": item.url,
                "summary": item.summary,
                "score": item.score,
                "author": item.author,
                "extra": item.extra,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            for item in items
        ]

        def _upsert() -> int:
            resp = (
                self._client.table(TABLE)
                .upsert(rows, on_conflict="source,external_id")
                .execute()
            )
            return len(resp.data or [])

        return await asyncio.to_thread(_upsert)

    async def delete_older_than(self, hours: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        def _delete() -> int:
            resp = (
                self._client.table(TABLE)
                .delete()
                .lt("fetched_at", cutoff)
                .execute()
            )
            return len(resp.data or [])

        return await asyncio.to_thread(_delete)

    async def fetch_recent(
        self, hours: int = 48, source: str | None = None, limit: int = 500
    ) -> list[dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        def _fetch() -> list[dict]:
            q = (
                self._client.table(TABLE)
                .select("*")
                .gte("fetched_at", cutoff)
                .order("score", desc=True)
                .limit(limit)
            )
            if source:
                q = q.eq("source", source)
            return q.execute().data or []

        return await asyncio.to_thread(_fetch)

    async def fetch_since(self, timestamp: datetime, limit: int = 500) -> list[dict]:
        def _fetch() -> list[dict]:
            resp = (
                self._client.table(TABLE)
                .select("*")
                .gt("created_at", timestamp.isoformat())
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return resp.data or []

        return await asyncio.to_thread(_fetch)

    async def cache_stats(self) -> dict:
        def _stats() -> dict:
            resp = (
                self._client.table(TABLE)
                .select("source,fetched_at")
                .execute()
            )
            rows = resp.data or []
            total = len(rows)
            per_source: dict[str, int] = {}
            last_updated = None
            for row in rows:
                per_source[row["source"]] = per_source.get(row["source"], 0) + 1
                fetched_at = row.get("fetched_at")
                if fetched_at and (last_updated is None or fetched_at > last_updated):
                    last_updated = fetched_at
            return {
                "total_items": total,
                "last_updated": last_updated,
                "per_source": per_source,
            }

        return await asyncio.to_thread(_stats)
