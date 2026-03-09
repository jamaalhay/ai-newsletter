"""
Refresh Twitter cookies using Playwright browser automation.

Logs into Twitter via a real browser to bypass Cloudflare,
extracts all cookies (including httpOnly auth_token), and
outputs them as base64-encoded JSON for use as a GitHub secret.

Usage:
    python scripts/refresh_cookies.py

Requires env vars: TWITTER_USERNAME, TWITTER_EMAIL, TWITTER_PASSWORD
Outputs base64-encoded cookies JSON to stdout.
"""

import asyncio
import base64
import json
import os
import sys

from playwright.async_api import async_playwright


async def refresh_cookies() -> str:
    username = os.environ["TWITTER_USERNAME"]
    email = os.environ["TWITTER_EMAIL"]
    password = os.environ["TWITTER_PASSWORD"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        # Navigate to login (use domcontentloaded — networkidle times out
        # because Twitter keeps WebSocket connections open)
        await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        # Enter email
        email_input = page.get_by_label("Phone, email, or username")
        await email_input.wait_for(state="visible", timeout=15000)
        await email_input.fill(email)
        await page.get_by_role("button", name="Next").click()
        await page.wait_for_timeout(2000)

        # Check for unusual activity challenge (username verification)
        challenge = page.get_by_label("Phone or username")
        if await challenge.is_visible():
            await challenge.fill(username)
            await page.get_by_test_id("ocfEnterTextNextButton").click()
            await page.wait_for_timeout(2000)

        # Enter password
        password_input = page.get_by_label("Password", exact=False)
        await password_input.wait_for(state="visible", timeout=10000)
        await password_input.fill(password)
        await page.get_by_test_id("LoginForm_Login_Button").click()

        # Wait for redirect to home
        try:
            await page.wait_for_url("**/home", timeout=15000)
        except Exception:
            # Check if we landed somewhere else valid
            if "x.com" not in page.url or "login" in page.url:
                print(f"Login failed — stuck at {page.url}", file=sys.stderr)
                await browser.close()
                sys.exit(1)

        await page.wait_for_timeout(2000)

        # Extract all cookies including httpOnly
        all_cookies = await context.cookies("https://x.com")
        cookies_dict = {c["name"]: c["value"] for c in all_cookies}

        # Verify we got the critical auth cookies
        if "auth_token" not in cookies_dict:
            print("Error: auth_token not found in cookies", file=sys.stderr)
            await browser.close()
            sys.exit(1)

        await browser.close()

    cookies_json = json.dumps(cookies_dict)
    return base64.b64encode(cookies_json.encode()).decode()


def main():
    b64 = asyncio.run(refresh_cookies())
    # Output only the base64 string to stdout
    print(b64)


if __name__ == "__main__":
    main()
