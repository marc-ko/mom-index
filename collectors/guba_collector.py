"""
东方财富股吧采集器 — 反检测升级版
支持板块: 纳斯达克ETF, 黄金ETF, 通信ETF(CPO), 半导体ETF
"""
import re
import html as html_mod
import requests
import os
from datetime import datetime
from typing import List, Dict

from .anti_detection import get_anti_detection

SECTORS = {
    "nasdaq":     {"name": "纳斯达克", "code": "of159941", "etf": "513100"},
    "gold":       {"name": "黄金",     "code": "of518880", "etf": "518880"},
    "cpo":        {"name": "CPO通信",  "code": "of515880", "etf": "515880"},
    "semiconductor": {"name": "半导体", "code": "of512480", "etf": "512480"},
}

def _get_proxy():
    """Use a proxy only when explicitly configured.

    Set MOM_INDEX_PROXY=http://host:port if you want traffic routed through a
    local proxy. By default we go direct; the old hardcoded 127.0.0.1:7890 made
    scraping fail whenever that proxy was not running.
    """
    proxy = os.environ.get("MOM_INDEX_PROXY", "").strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}

_ad = get_anti_detection()


def fetch_board(code: str) -> str:
    """获取股吧页面HTML — 使用反检测请求头"""
    url = f"https://guba.eastmoney.com/list,{code}.html"
    headers = _ad.get_common_headers(referer="https://guba.eastmoney.com")
    proxy = _get_proxy()
    try:
        resp = requests.get(url, headers=headers, proxies=proxy, timeout=15)
    except requests.exceptions.ProxyError:
        if not proxy:
            raise
        print(f"    代理不可用，改用直连: {code}")
        resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def parse_posts(html_content: str) -> List[Dict]:
    """解析帖子列表"""
    block_pattern = re.compile(
        r'<div\s+class="articleh\s+normal_post"[^>]*>(.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )
    span_pattern = re.compile(
        r'<span\s+class="(?P<class>l[1-5])"[^>]*>(?P<body>.*?)</span>',
        re.DOTALL | re.IGNORECASE,
    )
    link_pattern = re.compile(
        r'<a[^>]*href="(?P<href>/news,[^"]+)"[^>]*(?:title="(?P<title>[^"]*)")?[^>]*>(?P<text>.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    def clean_text(value: str) -> str:
        value = re.sub(r"<[^>]+>", "", value)
        return html_mod.unescape(value).strip()

    posts = []
    for block in block_pattern.findall(html_content):
        spans = {m.group("class").lower(): m.group("body") for m in span_pattern.finditer(block)}
        match = link_pattern.search(spans.get("l3", ""))
        if not match:
            continue

        url = match.group("href")
        title = html_mod.unescape((match.group("title") or clean_text(match.group("text"))).strip())
        if not title or title == '点击开始搜索':
            continue
        posts.append({
            "id": f"guba_{url.split(',')[-1].replace('.html','')}",
            "title": title,
            "url": f"https://guba.eastmoney.com{url}",
            "platform": "guba",
            "author": clean_text(spans.get("l4", "")) or "未知",
            "reads": clean_text(spans.get("l1", "")) or "0",
            "replies": clean_text(spans.get("l2", "")) or "0",
            "date": clean_text(spans.get("l5", "")) or "未知",
            "collected_at": datetime.now().isoformat(),
        })
    return posts


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有板块 — 带人类延迟防触发风控"""
    result = {}
    for sector_key, cfg in SECTORS.items():
        try:
            html = fetch_board(cfg["code"])
            posts = parse_posts(html)
            result[sector_key] = posts
            print(f"  [{cfg['name']}] 采集到 {len(posts)} 条帖子")
            # 板块之间加延迟
            _ad.sleep_like_human("scroll")
        except Exception as e:
            print(f"  [{cfg['name']}] 采集失败: {e}")
            result[sector_key] = []
    return result


if __name__ == "__main__":
    data = collect_all()
    for k, v in data.items():
        print(f"{k}: {len(v)} posts")


