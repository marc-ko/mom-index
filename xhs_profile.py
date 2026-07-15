"""
Open a persistent Playwright browser profile for Rednote/小红书 login only.

This script does not scrape, search, export, or print cookies. It only opens
XHS with a dedicated local profile so the session can be reused by the scraper.
Close the browser window or press Ctrl+C in the terminal to finish.
"""
import argparse
import asyncio
import os

from playwright.async_api import async_playwright

ROOT_DIR = os.path.dirname(__file__)
DEFAULT_PROFILE_DIR = os.path.join(ROOT_DIR, ".browser_profiles", "xhs")
DEFAULT_URL = "https://www.rednote.com/"

STEALTH_SCRIPTS = [
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
    "Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en-US','en']});",
    "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});",
]

async def main() -> None:
    parser = argparse.ArgumentParser(description="Open Rednote login profile only")
    parser.add_argument("--profile", default=os.environ.get("MOM_INDEX_XHS_PROFILE", DEFAULT_PROFILE_DIR))
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    os.makedirs(args.profile, exist_ok=True)
    print(f"Opening Rednote with persistent profile:")
    print(f"  {args.profile}")
    print("Log in in the browser window. This script will not scrape or export cookies.")
    print("Close the browser window, or press Ctrl+C here, when login is done.")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=args.profile,
            headless=False,
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        for script in STEALTH_SCRIPTS:
            await context.add_init_script(script)

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(args.url, wait_until="domcontentloaded", timeout=30000)

        try:
            while context.pages:
                await asyncio.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(main())

