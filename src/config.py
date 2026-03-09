from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "src" / "templates"
COOKIES_PATH = PROJECT_ROOT / "cookies.json"

# Twitter sources
TWITTER_SEARCH_QUERIES = [
    "AI model release",
    "GPT",
    "Claude AI",
    "LLM",
    "AI demo",
]
TWITTER_SEARCH_COUNT = 15

TWITTER_USERS = [
    "aaborovkov",
    "AndrewYNg",
    "ylecun",
    "sama",
    "karpathy",
]
TWITTER_USER_TWEET_COUNT = 10
TWITTER_TIMELINE_COUNT = 30

# Reddit sources
REDDIT_SUBREDDITS = [
    "MachineLearning",
    "artificial",
    "LocalLLaMA",
    "ChatGPT",
    "singularity",
]
REDDIT_POSTS_PER_SUB = 15
REDDIT_MIN_SCORE = 10
REDDIT_USER_AGENT = "ai-newsletter:v0.1 (by /u/{username})"

# Collection
RATE_LIMIT_DELAY = 3  # seconds between API calls

# Summarization
SUMMARIZE_MODEL = "claude-haiku-4-5-20251001"
DAILY_TOP_N = 30
WEEKLY_TOP_N = 60

# Composite ranking weights
RANK_WEIGHT_SCORE = 0.40
RANK_WEIGHT_ENGAGEMENT = 0.20
RANK_WEIGHT_SOURCE = 0.20
RANK_WEIGHT_RECENCY = 0.20

# Source quality multipliers (higher = more trusted/signal-rich)
SOURCE_WEIGHTS = {
    "reddit": {
        "MachineLearning": 2.0,
        "artificial": 1.5,
        "LocalLLaMA": 1.8,
        "ChatGPT": 1.0,
        "singularity": 0.8,
    },
    "twitter": {
        # High-signal accounts
        "karpathy": 2.5,
        "sama": 2.0,
        "ylecun": 2.0,
        "AndrewYNg": 2.0,
        # Timeline/search defaults
        "_default": 1.0,
    },
}
