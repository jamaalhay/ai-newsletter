import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic

from src.config import DAILY_TOP_N, OUTPUT_DIR, SUMMARIZE_MODEL, WEEKLY_TOP_N
from src.storage.jsonl import query_items
from src.summarizer.prompts import (
    DAILY_PROMPT,
    WEEKLY_PROMPT,
    format_items_for_prompt,
)

logger = logging.getLogger(__name__)


def _call_claude(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=SUMMARIZE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    # Strip markdown code fences if Claude wraps the HTML in them
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```html) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines)
    return text


def generate_daily(dry_run: bool = False) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    items = query_items(since=since, top_n=DAILY_TOP_N)
    if not items:
        logger.warning("No items found for daily summary")
        return ""

    logger.info(f"Generating daily summary from {len(items)} items")
    formatted = format_items_for_prompt(items)
    prompt = DAILY_PROMPT.format(items=formatted)

    if dry_run:
        print(f"--- DAILY PROMPT ({len(items)} items) ---")
        print(prompt[:2000])
        print("---")
        return ""

    summary_html = _call_claude(prompt)
    logger.info("Daily summary generated")
    return summary_html


def generate_weekly(dry_run: bool = False) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)

    items = query_items(since=since, top_n=WEEKLY_TOP_N)
    if not items:
        logger.warning("No items found for weekly summary")
        return ""

    # Collect daily summaries from this week
    daily_dir = OUTPUT_DIR / "daily"
    daily_summaries = []
    if daily_dir.exists():
        for html_file in sorted(daily_dir.glob("*.html"), reverse=True)[:7]:
            daily_summaries.append(html_file.read_text())

    logger.info(f"Generating weekly summary from {len(items)} items")
    formatted = format_items_for_prompt(items)
    prompt = WEEKLY_PROMPT.format(
        items=formatted,
        daily_summaries="\n---\n".join(daily_summaries) if daily_summaries else "(no daily summaries available)",
    )

    if dry_run:
        print(f"--- WEEKLY PROMPT ({len(items)} items) ---")
        print(prompt[:2000])
        print("---")
        return ""

    summary_html = _call_claude(prompt)
    logger.info("Weekly summary generated")
    return summary_html
