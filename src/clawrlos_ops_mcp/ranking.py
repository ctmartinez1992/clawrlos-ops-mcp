import math
from datetime import datetime, timezone

HALF_LIFE_HOURS = 12.0
MAX_PER_SOURCE = 3


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _recency_factor(fetched_at: str | None, now: datetime) -> float:
    ts = _parse_ts(fetched_at)
    if ts is None:
        return 0.5
    age_hours = max((now - ts).total_seconds() / 3600, 0)
    return 1 / (1 + age_hours / HALF_LIFE_HOURS)


def rank(items: list[dict], now: datetime | None = None) -> list[dict]:
    """Rank cached news rows across sources.

    Scores aren't comparable across sources (HN points vs. reddit upvotes
    vs. GitHub stars vs. HF trendingScore vs. lobsters score), so each
    source's scores are min-max normalized to 0..1 before combining with
    a recency decay. A soft per-source cap keeps any single source from
    flooding the result.
    """
    now = now or datetime.now(timezone.utc)

    by_source: dict[str, list[dict]] = {}
    for item in items:
        by_source.setdefault(item.get("source", "unknown"), []).append(item)

    scored: list[tuple[float, dict]] = []
    for _source, group in by_source.items():
        raw_scores = [float(g.get("score") or 0) for g in group]
        lo, hi = min(raw_scores), max(raw_scores)
        spread = hi - lo

        for item, raw in zip(group, raw_scores):
            if spread > 0:
                normalized = (raw - lo) / spread
            else:
                normalized = math.log1p(raw) / math.log1p(hi) if hi > 0 else 0.5
            combined = normalized * _recency_factor(item.get("fetched_at"), now)
            scored.append((combined, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    result: list[dict] = []
    per_source_count: dict[str, int] = {}
    for _combined, item in scored:
        source = item.get("source", "unknown")
        if per_source_count.get(source, 0) >= MAX_PER_SOURCE:
            continue
        per_source_count[source] = per_source_count.get(source, 0) + 1
        result.append(item)

    # Backfill with remaining items (beyond the per-source cap) if the
    # capped list doesn't reach the requested size — handled by the caller
    # slicing; here we append the leftovers in score order.
    capped_ids = {id(item) for item in result}
    leftovers = [item for _combined, item in scored if id(item) not in capped_ids]
    return result + leftovers
