DAILY_PROMPT = """You're writing a short AI news briefing for a non-technical audience.
Here are today's top items (ranked by a composite of popularity, discussion quality, source credibility, and recency):

{items}

Rules:
- Exactly 10 bullet points, each 1-3 sentences
- Group related items (same model launch = one item)
- Lead with biggest news
- Explain jargon in parentheses
- Include "Why it matters" angle
- Skip drama/memes — only concrete developments
- If fewer than 10 distinct stories exist, include notable discussion topics or emerging trends
- End with "Bottom line" one-liner
- Output valid HTML with <ul><li> structure
- Do NOT include <html>, <head>, or <body> tags — just the content HTML"""

WEEKLY_PROMPT = """Write a weekly AI roundup for a non-technical audience.
Here are the week's top items:

{items}

And here are the daily summaries from this week:

{daily_summaries}

Structure:
1. **Top 5-10 Developments** — 2-3 sentences each, wrapped in <h2> and <div> tags
2. **Trend of the Week** — one paragraph in a <div>
3. **Try It Yourself** — 2-3 simple demo project ideas in a <ul>

Keep it casual and accessible. Output valid HTML content (no <html>/<head>/<body> wrapper)."""


def format_items_for_prompt(items: list[dict]) -> str:
    lines = []
    for item in items:
        source = item["source"]
        author = item.get("author", "unknown")
        title = item.get("title") or ""
        content = (item.get("content") or "")[:300]
        score = item.get("score", 0)
        url = item.get("url", "")

        text = title if title else content
        lines.append(f"- [{source}] @{author} (score: {score}): {text}\n  URL: {url}")

    return "\n".join(lines)
