import logging
import time
from datetime import datetime, timezone

import requests

from src.config import (
    RATE_LIMIT_DELAY,
    REDDIT_MIN_SCORE,
    REDDIT_POSTS_PER_SUB,
    REDDIT_SUBREDDITS,
)

logger = logging.getLogger(__name__)

USER_AGENT = "ai-newsletter/0.1 (personal news aggregator)"


def collect() -> list[dict]:
    items = []
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    for sub_name in REDDIT_SUBREDDITS:
        try:
            logger.info(f"Fetching r/{sub_name} hot posts...")
            url = f"https://www.reddit.com/r/{sub_name}/hot.json"
            resp = session.get(url, params={"limit": REDDIT_POSTS_PER_SUB})
            resp.raise_for_status()
            data = resp.json()

            for post_data in data.get("data", {}).get("children", []):
                post = post_data["data"]

                if post.get("score", 0) < REDDIT_MIN_SCORE:
                    continue
                if post.get("stickied", False):
                    continue

                selftext = post.get("selftext", "") or ""
                author = post.get("author", "[deleted]") or "[deleted]"
                is_self = post.get("is_self", True)

                items.append({
                    "id": f"rd_{post['id']}",
                    "source": "reddit",
                    "title": post.get("title", ""),
                    "content": selftext[:1000],
                    "author": author,
                    "url": f"https://reddit.com{post['permalink']}",
                    "score": post.get("score", 0),
                    "engagement": post.get("num_comments", 0),
                    "metadata": {
                        "subreddit": sub_name,
                        "upvote_ratio": post.get("upvote_ratio", 0),
                        "num_comments": post.get("num_comments", 0),
                        "is_self": is_self,
                        "link_url": post.get("url") if not is_self else None,
                    },
                    "published_at": datetime.fromtimestamp(
                        post.get("created_utc", 0), tz=timezone.utc
                    ).isoformat(),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })

            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            logger.error(f"Error fetching r/{sub_name}: {e}")

    logger.info(f"Reddit: collected {len(items)} items")
    return items


def collect_reddit() -> list[dict]:
    return collect()
