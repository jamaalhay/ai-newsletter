import json
import math
from datetime import datetime, timezone
from pathlib import Path

from src.config import (
    DATA_DIR,
    RANK_WEIGHT_ENGAGEMENT,
    RANK_WEIGHT_RECENCY,
    RANK_WEIGHT_SCORE,
    RANK_WEIGHT_SOURCE,
    SOURCE_WEIGHTS,
)

ITEMS_FILE = DATA_DIR / "items.jsonl"


def _ensure_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ITEMS_FILE.exists():
        ITEMS_FILE.touch()


def load_ids() -> set[str]:
    _ensure_file()
    ids = set()
    with open(ITEMS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                ids.add(json.loads(line)["id"])
    return ids


def append_items(items: list[dict]) -> int:
    _ensure_file()
    existing_ids = load_ids()
    added = 0
    with open(ITEMS_FILE, "a") as f:
        for item in items:
            if item["id"] not in existing_ids:
                f.write(json.dumps(item, default=str) + "\n")
                existing_ids.add(item["id"])
                added += 1
    return added


def _compute_rank(item: dict, now: datetime, max_score: float, max_engagement: float) -> float:
    """Composite ranking: score, engagement ratio, source quality, recency."""
    # Normalized raw score (log scale to dampen viral outliers)
    raw_score = item.get("score", 0) or 0
    score_norm = math.log1p(raw_score) / math.log1p(max_score) if max_score > 0 else 0

    # Engagement ratio: comments relative to score (high ratio = discussion-worthy)
    engagement = item.get("engagement", 0) or 0
    eng_norm = math.log1p(engagement) / math.log1p(max_engagement) if max_engagement > 0 else 0

    # Source quality multiplier
    source = item.get("source", "")
    source_weights = SOURCE_WEIGHTS.get(source, {})
    if source == "reddit":
        sub = item.get("metadata", {}).get("subreddit", "")
        source_mult = source_weights.get(sub, 1.0)
    elif source == "twitter":
        author = item.get("author", "")
        source_mult = source_weights.get(author, source_weights.get("_default", 1.0))
    else:
        source_mult = 1.0
    # Normalize to 0-1 (max multiplier is ~2.5)
    source_norm = min(source_mult / 2.5, 1.0)

    # Recency: hours old → decay (24h old = 0.5, 0h old = 1.0)
    collected = datetime.fromisoformat(item["collected_at"])
    if collected.tzinfo is None:
        collected = collected.replace(tzinfo=timezone.utc)
    hours_old = max((now - collected).total_seconds() / 3600, 0)
    recency_norm = 1.0 / (1.0 + hours_old / 24.0)

    rank = (
        RANK_WEIGHT_SCORE * score_norm
        + RANK_WEIGHT_ENGAGEMENT * eng_norm
        + RANK_WEIGHT_SOURCE * source_norm
        + RANK_WEIGHT_RECENCY * recency_norm
    )
    return rank


def query_items(
    since: datetime | None = None,
    until: datetime | None = None,
    top_n: int | None = None,
) -> list[dict]:
    _ensure_file()
    now = datetime.now(timezone.utc)
    items = []
    with open(ITEMS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            pub = datetime.fromisoformat(item["collected_at"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if since and pub < since:
                continue
            if until and pub > until:
                continue
            items.append(item)

    if not items:
        return items

    # Compute composite ranks
    max_score = max((i.get("score", 0) or 0) for i in items)
    max_engagement = max((i.get("engagement", 0) or 0) for i in items)
    for item in items:
        item["_rank"] = _compute_rank(item, now, max_score, max_engagement)

    items.sort(key=lambda x: x["_rank"], reverse=True)
    if top_n:
        items = items[:top_n]
    return items


def item_count() -> int:
    _ensure_file()
    count = 0
    with open(ITEMS_FILE) as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def last_collected_at() -> str | None:
    _ensure_file()
    last = None
    with open(ITEMS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                last = json.loads(line).get("collected_at")
    return last
