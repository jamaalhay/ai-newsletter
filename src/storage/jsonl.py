import json
from datetime import datetime, timezone
from pathlib import Path

from src.config import DATA_DIR

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


def query_items(
    since: datetime | None = None,
    until: datetime | None = None,
    top_n: int | None = None,
) -> list[dict]:
    _ensure_file()
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

    items.sort(key=lambda x: x.get("score", 0) or 0, reverse=True)
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
