import logging
import os
from datetime import datetime, timezone

import praw

from src.config import (
    REDDIT_MIN_SCORE,
    REDDIT_POSTS_PER_SUB,
    REDDIT_SUBREDDITS,
    REDDIT_USER_AGENT,
)

logger = logging.getLogger(__name__)


def collect() -> list[dict]:
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    if not all([client_id, client_secret, username, password]):
        logger.error("Reddit credentials not configured")
        return []

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent=REDDIT_USER_AGENT.format(username=username),
    )

    items = []
    for sub_name in REDDIT_SUBREDDITS:
        try:
            logger.info(f"Fetching r/{sub_name} hot posts...")
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.hot(limit=REDDIT_POSTS_PER_SUB):
                if post.score < REDDIT_MIN_SCORE:
                    continue
                if post.stickied:
                    continue

                items.append({
                    "id": f"rd_{post.id}",
                    "source": "reddit",
                    "title": post.title,
                    "content": post.selftext[:1000] if post.selftext else "",
                    "author": str(post.author) if post.author else "[deleted]",
                    "url": f"https://reddit.com{post.permalink}",
                    "score": post.score,
                    "engagement": post.num_comments,
                    "metadata": {
                        "subreddit": sub_name,
                        "upvote_ratio": post.upvote_ratio,
                        "num_comments": post.num_comments,
                        "is_self": post.is_self,
                        "link_url": post.url if not post.is_self else None,
                    },
                    "published_at": datetime.fromtimestamp(
                        post.created_utc, tz=timezone.utc
                    ).isoformat(),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            logger.error(f"Error fetching r/{sub_name}: {e}")

    logger.info(f"Reddit: collected {len(items)} items")
    return items


def collect_reddit() -> list[dict]:
    return collect()
