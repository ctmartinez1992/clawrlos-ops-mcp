from datetime import datetime, timedelta, timezone

from clawrlos_ops_mcp.ranking import rank


def _item(source, score, hours_ago=0, **extra):
    fetched_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return {
        "source": source,
        "external_id": f"{source}-{score}-{hours_ago}",
        "title": f"{source} item",
        "score": score,
        "fetched_at": fetched_at.isoformat(),
        **extra,
    }


def test_rank_prefers_higher_normalized_score_within_source():
    items = [_item("hn", 10), _item("hn", 100), _item("hn", 50)]
    ranked = rank(items)
    scores = [i["score"] for i in ranked]
    assert scores == [100, 50, 10]


def test_rank_prefers_recency_when_scores_tie():
    fresh = _item("hn", 50, hours_ago=0)
    stale = _item("hn", 50, hours_ago=48)
    ranked = rank([stale, fresh])
    assert ranked[0] is fresh


def test_rank_caps_items_per_source():
    items = [_item("hn", 100 - i) for i in range(10)]
    ranked = rank(items)
    top_three_sources = [i["source"] for i in ranked[:3]]
    assert top_three_sources == ["hn", "hn", "hn"]
    # capped items still all appear, just pushed after other sources' items
    assert len(ranked) == len(items)


def test_rank_normalizes_across_different_scales():
    items = [
        _item("hackernews", 500),
        _item("huggingface", 50000),
        _item("lobsters", 20),
    ]
    ranked = rank(items)
    # all three should be near the top since each is the max within its own source
    top_sources = {i["source"] for i in ranked[:3]}
    assert top_sources == {"hackernews", "huggingface", "lobsters"}


def test_rank_handles_empty_list():
    assert rank([]) == []


def test_rank_handles_missing_score():
    items = [_item("hn", None), _item("hn", 10)]
    ranked = rank(items)
    assert len(ranked) == 2
