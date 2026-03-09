"""
Refresh Twitter cookies using Playwright browser automation.

Run this LOCALLY when the collect workflow reports expired cookies.
It logs into Twitter via a real browser, extracts all cookies
(including httpOnly auth_token), and updates the GitHub secret.

Usage:
    uv run python scripts/refresh_cookies.py

Requires env vars: TWITTER_USERNAME, TWITTER_EMAIL, TWITTER_PASSWORD
(or source your .env first)
"""

import asyncio
import base64
import json
import os
import subprocess
import sys

from playwright.async_api import async_playwright


async def refresh_cookies() -> dict:
    username = os.environ["TWITTER_USERNAME"]
    email = os.environ["TWITTER_EMAIL"]
    password = os.environ["TWITTER_PASSWORD"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print("Navigating to login page...")
        await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        print("Entering email...")
        email_input = page.get_by_label("Phone, email, or username")
        await email_input.wait_for(state="visible", timeout=30000)
        await email_input.fill(email)
        await page.get_by_role("button", name="Next").click()
        await page.wait_for_timeout(3000)

        # Handle unusual activity challenge
        challenge = page.get_by_label("Phone or username")
        challenge_alt = page.get_by_test_id("ocfEnterTextTextInput")
        if await challenge.is_visible() or await challenge_alt.is_visible():
            print("Username verification required, entering username...")
            target = challenge if await challenge.is_visible() else challenge_alt
            await target.fill(username)
            try:
                await page.get_by_test_id("ocfEnterTextNextButton").click()
            except Exception:
                await page.get_by_role("button", name="Next").click()
            await page.wait_for_timeout(3000)

        print("Entering password...")
        password_input = page.get_by_label("Password", exact=False)
        await password_input.wait_for(state="visible", timeout=30000)
        await password_input.fill(password)
        await page.get_by_test_id("LoginForm_Login_Button").click()

        print("Waiting for login...")
        await page.wait_for_url("**/home", timeout=30000)
        await page.wait_for_timeout(2000)
        print("Login successful!")

        all_cookies = await context.cookies("https://x.com")
        cookies_dict = {c["name"]: c["value"] for c in all_cookies}

        if "auth_token" not in cookies_dict:
            print("ERROR: auth_token not in cookies!")
            await browser.close()
            sys.exit(1)

        print(f"Extracted {len(cookies_dict)} cookies")
        await browser.close()

    return cookies_dict


def main():
    cookies = asyncio.run(refresh_cookies())

    # Save locally
    cookies_path = os.path.join(os.path.dirname(__file__), "..", "cookies.json")
    with open(cookies_path, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"Saved to {cookies_path}")

    # Update GitHub secret
    b64 = base64.b64encode(json.dumps(cookies).encode()).decode()
    result = subprocess.run(
        ["gh", "secret", "set", "TWITTER_COOKIES_B64", "--body", b64],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("GitHub secret TWITTER_COOKIES_B64 updated!")
    else:
        print(f"Failed to update GitHub secret: {result.stderr}")
        print("Run manually: gh secret set TWITTER_COOKIES_B64 --body <base64>")


if __name__ == "__main__":
    main()
