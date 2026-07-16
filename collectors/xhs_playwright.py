"""
小红书 Playwright 采集器

Uses one persistent browser profile so you can log in once and reuse the saved
session. Cookies are kept inside the local Playwright profile; they are not
printed or exported.
"""
import argparse
import asyncio
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List
from urllib.parse import quote, urljoin

from playwright.async_api import BrowserContext, Page, async_playwright
from .anti_detection import get_anti_detection

_ad = get_anti_detection()

SEARCH_KEYWORDS = {
    "nasdaq": ["美股怎么买", "纳斯达克新手", "纳指还能买吗"],
    "gold": ["黄金怎么买", "黄金亏了", "黄金还能涨吗"],
    "cpo": ["CPO是什么", "CPO还能买吗"],
    "semiconductor": ["芯片还能上车吗", "半导体新手"],
}

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "xhs_posts.json")
PROFILE_DIR = os.environ.get(
    "MOM_INDEX_XHS_PROFILE",
    os.path.join(ROOT_DIR, ".browser_profiles", "xhs"),
)
HEADLESS = os.environ.get("MOM_INDEX_XHS_HEADLESS", "0").lower() in {"1", "true", "yes"}
LOGIN_WAIT_SECONDS = int(os.environ.get("MOM_INDEX_XHS_LOGIN_WAIT", "600"))
REDNOTE_BASE_URL = os.environ.get("MOM_INDEX_REDNOTE_BASE_URL", "https://www.rednote.com").rstrip("/")
KEEP_OPEN_AFTER_LOGIN = os.environ.get("MOM_INDEX_XHS_KEEP_OPEN", "0").lower() in {"1", "true", "yes"}

LOGIN_HINTS = ("登录", "手机号", "验证码", "扫码", "二维码")


def _looks_like_login(html: str, url: str) -> bool:
    sample = html[:8000]
    if "login" in url.lower():
        return True
    return "登录" in sample and any(hint in sample for hint in LOGIN_HINTS[1:])


async def _new_context(playwright) -> BrowserContext:
    os.makedirs(os.path.join(PROFILE_DIR, "Default"), exist_ok=True)
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=HEADLESS,
        args=_ad.get_playwright_launch_args(),
        viewport={"width": 1366, "height": 768},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        device_scale_factor=1,
    )
    for script in _ad.get_stealth_scripts():
        await context.add_init_script(script)
    return context


async def _wait_for_login(page: Page, reason: str) -> None:
    if HEADLESS:
        return

    print(f"    {reason}")
    print(f"    请在打开的小红书窗口完成登录；最多等待 {LOGIN_WAIT_SECONDS} 秒。")
    print(f"    登录会保存在: {PROFILE_DIR}")

    for _ in range(LOGIN_WAIT_SECONDS):
        await asyncio.sleep(1)
        html = await page.content()
        if not _looks_like_login(html, page.url):
            print("    登录状态看起来已保存，继续采集。")
            await asyncio.sleep(3)
            return

    print("    登录等待结束；如果仍未登录，本次 XHS 采集可能为空。")


async def login_only() -> None:
    async with async_playwright() as p:
        context = await _new_context(p)
        page = await context.new_page()
        try:
            await page.goto(f"{REDNOTE_BASE_URL}/explore", wait_until="domcontentloaded", timeout=30000)
            await _wait_for_login(page, "打开了小红书登录窗口。")
            if KEEP_OPEN_AFTER_LOGIN and not HEADLESS:
                print("    MOM_INDEX_XHS_KEEP_OPEN=1，窗口将继续保持打开。关闭窗口或中断命令即可结束。")
                while True:
                    await asyncio.sleep(5)
        finally:
            if not KEEP_OPEN_AFTER_LOGIN:
                await context.close()


async def _safe_goto(page: Page, url: str) -> None:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        message = str(e)
        if "ERR_ABORTED" in message or "frame was detached" in message:
            await asyncio.sleep(5)
            return
        raise


async def _extract_posts(page: Page, keyword: str, limit: int) -> List[Dict]:
    posts: List[Dict] = []
    encoded = quote(keyword)
    search_url = f"{REDNOTE_BASE_URL}/search_result?keyword={encoded}&type=51"
    await _safe_goto(page, search_url)
    await asyncio.sleep(6)

    html = await page.content()
    if _looks_like_login(html, page.url):
        await _wait_for_login(page, f"搜索 '{keyword}' 时发现需要登录。")
        await _safe_goto(page, search_url)
        await asyncio.sleep(6)
        html = await page.content()

    await page.mouse.wheel(0, 1400)
    await asyncio.sleep(2)
    html = await page.content()

    if "安全限制" in html or "300012" in html:
        print(f"    ⚠️ XHS 风控拦截: {keyword}")
        return posts

    if _looks_like_login(html, page.url):
        print(f"    ⚠️ XHS 仍需要登录: {keyword}")
        return posts

    items = await page.locator("section.note-item").evaluate_all(
        """
        els => els.map(section => {
          const titleEl = section.querySelector('a.title, .title');
          const linkEl =
            section.querySelector('a.title[href]') ||
            section.querySelector('a[href*="/explore/"]') ||
            section.querySelector('a[href*="/discovery/item"]') ||
            section.querySelector('a[href]');
          return {
            title: (titleEl?.innerText || titleEl?.textContent || '').trim(),
            href: linkEl?.getAttribute('href') || linkEl?.href || ''
          };
        }).filter(item => item.title)
        """
    )

    seen = set()
    for item in items:
        title = item["title"][:100]
        url = urljoin(f"{REDNOTE_BASE_URL}/", item.get("href") or "")
        key = f"{keyword}\0{url}\0{title}"
        if key in seen:
            continue
        seen.add(key)
        post_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        posts.append({
            "id": f"xhs_{post_id}",
            "title": title,
            "url": url,
            "platform": "xiaohongshu",
            "keyword": keyword,
            "collected_at": datetime.now().isoformat(),
        })
        if len(posts) >= limit:
            break
    print(f"    '{keyword}' -> {len(posts)}条")
    return posts


async def _collect_all_async() -> Dict[str, List[Dict]]:
    result: Dict[str, List[Dict]] = {}
    async with async_playwright() as p:
        context = await _new_context(p)
        page = await context.new_page()
        try:
            for sector_key, keywords in SEARCH_KEYWORDS.items():
                all_notes: List[Dict] = []
                for kw in keywords:
                    try:
                        if page.is_closed():
                            page = await context.new_page()
                        notes = await _extract_posts(page, kw, limit=8)
                        all_notes.extend(notes)
                        _ad.sleep_like_human("search")
                    except Exception as e:
                        print(f"  [XHS-{sector_key}] '{kw}' 失败: {e}")
                        try:
                            if page.is_closed():
                                page = await context.new_page()
                        except Exception:
                            page = await context.new_page()

                seen = set()
                unique = []
                for note in all_notes:
                    key = note.get("id") or note.get("title")
                    if key not in seen:
                        seen.add(key)
                        unique.append(note)
                result[sector_key] = unique
        finally:
            await context.close()
    return result


def collect_all() -> Dict[str, List[Dict]]:
    return asyncio.run(_collect_all_async())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", action="store_true", help="open XHS and wait for login only")
    args = parser.parse_args()

    if args.login:
        asyncio.run(login_only())
        return

    data = collect_all()
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    total = sum(len(v) for v in data.values())
    print(f"\n共采集 {total} 条 XHS 帖子 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()





