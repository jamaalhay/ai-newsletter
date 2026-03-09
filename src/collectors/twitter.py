import asyncio
import base64
import logging
import os
from datetime import datetime, timezone

import twikit

from src.config import (
    COOKIES_PATH,
    RATE_LIMIT_DELAY,
    TWITTER_SEARCH_COUNT,
    TWITTER_SEARCH_QUERIES,
    TWITTER_TIMELINE_COUNT,
    TWITTER_USER_TWEET_COUNT,
    TWITTER_USERS,
)

logger = logging.getLogger(__name__)


async def _get_client() -> twikit.Client:
    client = twikit.Client("en-US")

    # Decode cookies from env if present (GitHub Actions)
    cookies_b64 = os.getenv("TWITTER_COOKIES_B64")
    if cookies_b64 and not COOKIES_PATH.exists():
        COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        COOKIES_PATH.write_bytes(base64.b64decode(cookies_b64))

    if COOKIES_PATH.exists():
        client.load_cookies(COOKIES_PATH)
    else:
        username = os.getenv("TWITTER_USERNAME")
        email = os.getenv("TWITTER_EMAIL")
        password = os.getenv("TWITTER_PASSWORD")
        if not all([username, email, password]):
            raise RuntimeError("Twitter credentials not configured")
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
        )
        COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        client.save_cookies(COOKIES_PATH)

    return client


def _tweet_to_item(tweet) -> dict:
    legacy = tweet._legacy if hasattr(tweet, "_legacy") else {}
    core = tweet._data.get("core", {}) if hasattr(tweet, "_data") else {}
    user = core.get("user_results", {}).get("result", {}).get("legacy", {})

    text = legacy.get("full_text", "")
    username = user.get("screen_name", "unknown")
    tweet_id = getattr(tweet, "id", "")
    likes = legacy.get("favorite_count", 0)
    retweets = legacy.get("retweet_count", 0)
    replies = legacy.get("reply_count", 0)
    quotes = legacy.get("quote_count", 0)
    engagement = likes + retweets + replies + quotes

    return {
        "id": f"tw_{tweet_id}",
        "source": "twitter",
        "title": None,
        "content": text,
        "author": username,
        "url": f"https://x.com/{username}/status/{tweet_id}",
        "score": likes,
        "engagement": engagement,
        "metadata": {
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "quotes": quotes,
        },
        "published_at": legacy.get("created_at", ""),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


async def collect() -> list[dict]:
    items = []
    try:
        client = await _get_client()
    except Exception as e:
        logger.error(f"Twitter auth failed: {e}")
        return items

    # Timeline
    try:
        logger.info("Fetching Twitter timeline...")
        tweets = await client.get_timeline(count=TWITTER_TIMELINE_COUNT)
        items.extend(_tweet_to_item(t) for t in tweets)
        await asyncio.sleep(RATE_LIMIT_DELAY)
    except twikit.errors.TooManyRequests:
        logger.warning("Rate limited on timeline, skipping")
    except Exception as e:
        logger.error(f"Timeline error: {e}")

    # Search queries
    for query in TWITTER_SEARCH_QUERIES:
        try:
            logger.info(f"Searching Twitter: {query}")
            tweets = await client.search_tweet(query, "Top", count=TWITTER_SEARCH_COUNT)
            items.extend(_tweet_to_item(t) for t in tweets)
            await asyncio.sleep(RATE_LIMIT_DELAY)
        except twikit.errors.TooManyRequests:
            logger.warning(f"Rate limited on search '{query}', skipping")
        except Exception as e:
            logger.error(f"Search error for '{query}': {e}")

    # Specific users
    for username in TWITTER_USERS:
        try:
            logger.info(f"Fetching tweets from @{username}")
            user = await client.get_user_by_screen_name(username)
            if user:
                tweets = await client.get_user_tweets(
                    user_id=user.id,
                    tweet_type="Tweets",
                    count=TWITTER_USER_TWEET_COUNT,
                )
                items.extend(_tweet_to_item(t) for t in tweets)
            await asyncio.sleep(RATE_LIMIT_DELAY)
        except twikit.errors.TooManyRequests:
            logger.warning(f"Rate limited on @{username}, skipping")
        except Exception as e:
            logger.error(f"User tweets error for @{username}: {e}")

    if not items:
        logger.error(
            "TWITTER_COOKIES_EXPIRED: collected 0 items. "
            "Refresh cookies locally: source .env && uv run python scripts/refresh_cookies.py"
        )

    logger.info(f"Twitter: collected {len(items)} items")
    return items


async def collect_twitter() -> list[dict]:
    return await collect()
