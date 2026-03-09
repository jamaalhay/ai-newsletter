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

        try:
            # Navigate to login
            print("Navigating to login page...", file=sys.stderr)
            await page.goto(
                "https://x.com/i/flow/login",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await page.wait_for_timeout(5000)

            # Enter email
            print("Entering email...", file=sys.stderr)
            email_input = page.get_by_label("Phone, email, or username")
            await email_input.wait_for(state="visible", timeout=30000)
            await email_input.fill(email)
            await page.get_by_role("button", name="Next").click()
            await page.wait_for_timeout(3000)

            # Check for unusual activity challenge (username verification)
            # Try multiple possible selectors
            challenge = page.get_by_label("Phone or username")
            challenge_alt = page.get_by_test_id("ocfEnterTextTextInput")
            if await challenge.is_visible() or await challenge_alt.is_visible():
                print("Unusual activity challenge detected, entering username...", file=sys.stderr)
                target = challenge if await challenge.is_visible() else challenge_alt
                await target.fill(username)
                # Try both possible button selectors
                try:
                    await page.get_by_test_id("ocfEnterTextNextButton").click()
                except Exception:
                    await page.get_by_role("button", name="Next").click()
                await page.wait_for_timeout(3000)

            # Enter password — wait longer and try multiple selectors
            print("Entering password...", file=sys.stderr)
            password_input = page.get_by_label("Password", exact=False)
            try:
                await password_input.wait_for(state="visible", timeout=20000)
            except Exception:
                # Take screenshot for debugging
                await page.screenshot(path="/tmp/twitter_login_debug.png")
                print(f"Password field not found. Current URL: {page.url}", file=sys.stderr)
                print("Screenshot saved to /tmp/twitter_login_debug.png", file=sys.stderr)
                # Try to print what's on page
                content = await page.content()
                print(f"Page content length: {len(content)}", file=sys.stderr)
                raise

            await password_input.fill(password)
            await page.get_by_test_id("LoginForm_Login_Button").click()

            # Wait for redirect to home
            print("Waiting for login redirect...", file=sys.stderr)
            try:
                await page.wait_for_url("**/home", timeout=20000)
            except Exception:
                if "x.com" not in page.url or "login" in page.url:
                    await page.screenshot(path="/tmp/twitter_login_debug.png")
                    print(f"Login failed — stuck at {page.url}", file=sys.stderr)
                    await browser.close()
                    sys.exit(1)

            await page.wait_for_timeout(2000)
            print("Login successful!", file=sys.stderr)

            # Extract all cookies including httpOnly
            all_cookies = await context.cookies("https://x.com")
            cookies_dict = {c["name"]: c["value"] for c in all_cookies}

            if "auth_token" not in cookies_dict:
                print("Error: auth_token not found in cookies", file=sys.stderr)
                print(f"Available cookies: {list(cookies_dict.keys())}", file=sys.stderr)
                await browser.close()
                sys.exit(1)

            print(f"Extracted {len(cookies_dict)} cookies", file=sys.stderr)

        except Exception as e:
            # Upload screenshot as artifact if available
            try:
                await page.screenshot(path="/tmp/twitter_login_debug.png")
                print("Debug screenshot saved to /tmp/twitter_login_debug.png", file=sys.stderr)
            except Exception:
                pass
            await browser.close()
            raise

        await browser.close()

    cookies_json = json.dumps(cookies_dict)
    return base64.b64encode(cookies_json.encode()).decode()


def main():
    b64 = asyncio.run(refresh_cookies())
    # Output only the base64 string to stdout
    print(b64)


if __name__ == "__main__":
    main()
