import logging
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.config import OUTPUT_DIR, TEMPLATES_DIR

logger = logging.getLogger(__name__)

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)


def render_daily(summary_html: str, items: list[dict], date: datetime | None = None):
    date = date or datetime.now(timezone.utc)
    date_str = date.strftime("%Y-%m-%d")

    template = _env.get_template("daily.html.j2")
    html = template.render(
        date=date_str,
        summary=summary_html,
        top_items=items[:30],
        all_items=items,
    )

    out_dir = OUTPUT_DIR / "daily"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_str}.html"
    out_path.write_text(html)
    logger.info(f"Wrote daily summary to {out_path}")

    _rebuild_index()
    return out_path


def render_weekly(summary_html: str, items: list[dict], date: datetime | None = None):
    date = date or datetime.now(timezone.utc)
    date_str = date.strftime("%Y-%m-%d")

    template = _env.get_template("weekly.html.j2")
    html = template.render(
        date=date_str,
        summary=summary_html,
        top_items=items[:60],
    )

    out_dir = OUTPUT_DIR / "weekly"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_str}.html"
    out_path.write_text(html)
    logger.info(f"Wrote weekly summary to {out_path}")

    _rebuild_index()
    return out_path


def _rebuild_index():
    daily_dir = OUTPUT_DIR / "daily"
    weekly_dir = OUTPUT_DIR / "weekly"

    dailies = sorted(daily_dir.glob("*.html"), reverse=True) if daily_dir.exists() else []
    weeklies = sorted(weekly_dir.glob("*.html"), reverse=True) if weekly_dir.exists() else []

    template = _env.get_template("index.html.j2")
    html = template.render(
        dailies=[f.stem for f in dailies],
        weeklies=[f.stem for f in weeklies],
    )

    index_path = OUTPUT_DIR / "index.html"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path.write_text(html)
    logger.info(f"Rebuilt index at {index_path}")
