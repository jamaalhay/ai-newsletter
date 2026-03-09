import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from src.collectors.reddit import collect_reddit
from src.collectors.twitter import collect_twitter
from src.delivery.html_renderer import render_daily, render_weekly
from src.storage.jsonl import append_items, item_count, last_collected_at, query_items
from src.summarizer.claude import generate_daily, generate_weekly

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_collect(args):
    all_items = []

    if args.source in ("all", "twitter"):
        twitter_items = asyncio.run(collect_twitter())
        all_items.extend(twitter_items)

    if args.source in ("all", "reddit"):
        reddit_items = collect_reddit()
        all_items.extend(reddit_items)

    added = append_items(all_items)
    logger.info(f"Collected {len(all_items)} items, {added} new (deduped)")


def cmd_daily(args):
    summary_html = generate_daily(dry_run=args.dry_run)
    if args.dry_run or not summary_html:
        return

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    items = query_items(since=since)

    path = render_daily(summary_html, items, date=now)
    logger.info(f"Daily summary written to {path}")


def cmd_weekly(args):
    summary_html = generate_weekly(dry_run=args.dry_run)
    if args.dry_run or not summary_html:
        return

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    items = query_items(since=since)

    path = render_weekly(summary_html, items, date=now)
    logger.info(f"Weekly summary written to {path}")


def cmd_status(args):
    count = item_count()
    last = last_collected_at()
    print(f"Total items: {count}")
    print(f"Last collected: {last or 'never'}")


def main():
    parser = argparse.ArgumentParser(prog="ai-newsletter", description="AI Newsletter Pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="Run collectors")
    p_collect.add_argument("--source", choices=["all", "twitter", "reddit"], default="all")
    p_collect.set_defaults(func=cmd_collect)

    p_daily = sub.add_parser("daily", help="Generate daily summary")
    p_daily.add_argument("--dry-run", action="store_true", help="Preview without writing")
    p_daily.set_defaults(func=cmd_daily)

    p_weekly = sub.add_parser("weekly", help="Generate weekly roundup")
    p_weekly.add_argument("--dry-run", action="store_true", help="Preview without writing")
    p_weekly.set_defaults(func=cmd_weekly)

    p_status = sub.add_parser("status", help="Show collection status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
