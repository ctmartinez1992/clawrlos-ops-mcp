import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .config import settings
from .db import SupabaseStore
from .scrapers import ALL_SCRAPERS
from .scrapers.base import build_http_client

log = logging.getLogger(__name__)


async def run_refresh_cycle(db: SupabaseStore) -> None:
    async with build_http_client() as client:
        results = await asyncio.gather(
            *(scraper(client) for scraper in ALL_SCRAPERS), return_exceptions=True
        )

    items = []
    for scraper, result in zip(ALL_SCRAPERS, results):
        if isinstance(result, Exception):
            log.warning(
                "scraper %s failed: %s", getattr(scraper, "__name__", scraper), result
            )
            continue
        items.extend(result)

    upserted = await db.upsert_items(items)
    deleted = await db.delete_older_than(hours=settings.retention_hours)
    log.info(
        "refresh cycle complete: %d items upserted, %d stale rows deleted",
        upserted,
        deleted,
    )


def _seconds_until_next_cycle() -> float:
    return settings.refresh_interval_hours * 3600


async def refresh_loop(db: SupabaseStore) -> None:
    try:
        stats = await db.cache_stats()
        last_updated_raw = stats.get("last_updated")
        should_refresh_now = True

        if last_updated_raw:
            last_updated = datetime.fromisoformat(
                last_updated_raw.replace("Z", "+00:00")
            )
            age = datetime.now(timezone.utc) - last_updated
            should_refresh_now = age >= timedelta(hours=settings.refresh_interval_hours)

        if should_refresh_now:
            await run_refresh_cycle(db)
    except Exception:
        log.exception("initial refresh check failed")

    while True:
        await asyncio.sleep(_seconds_until_next_cycle())
        try:
            await run_refresh_cycle(db)
        except Exception:
            log.exception("refresh cycle failed")
