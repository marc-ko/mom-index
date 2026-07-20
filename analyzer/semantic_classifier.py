import hashlib
import json
import os
import re
from pathlib import Path
from typing import Dict

import requests

from analyzer.semantic_types import SemanticClassification


CLASSIFIER_VERSION = "semantic-openrouter-free-v2"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_REMOTE_MODEL = "openrouter/free"
CACHE_FILE = Path(__file__).resolve().parents[1] / ".semantic_cache.json"
DEFAULT_OPENROUTER_ATTEMPTS = 3
MALFORMED_RESPONSE_ERRORS = (json.JSONDecodeError, TypeError, AttributeError, KeyError, IndexError)

BEGINNER_WORDS = ("小白", "新手", "新人", "萌新", "第一次", "刚入")
GUIDE_WORDS = ("指南", "攻略", "必看", "一图看懂", "看这篇", "教你", "入门")
QUESTION_WORDS = ("请问", "有没有人", "谁知道", "求助", "大佬", "懂啊")
DECISION_WORDS = ("该不该", "要不要", "能不能", "还能上车吗", "还会涨吗", "还会跌吗", "可以买吗")
BASIC_GAP_WORDS = ("怎么算", "什么意思", "怎么买", "在哪看", "回本", "盈利")
MARKETING_WORDS = ("领取", "资料", "私信", "评论区", "课程", "进群", "带你", "无脑")
PRO_WORDS = ("估值", "溢价率", "PE", "PB", "ROE", "基本面", "仓位", "对冲", "网格")
BUY_WORDS = ("上车", "买", "加仓", "抄底", "满仓", "冲")
SELL_WORDS = ("割肉", "清仓", "止损", "跑", "赎回")
PANIC_WORDS = ("完了", "亏", "慌", "崩", "跌麻", "救命")
FOMO_WORDS = ("起飞", "梭哈", "稳赚", "必涨", "暴富")


def _count(text: str, words) -> int:
    return sum(1 for word in words if word.lower() in text.lower())


def _cache_key(post: Dict, sector: str) -> str:
    post_id = post.get("id") or ""
    text = json.dumps(
        {"id": post_id, "title": post.get("title", ""), "content": post.get("content", ""), "sector": sector},
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{CLASSIFIER_VERSION}:{digest}"


def _read_cache() -> Dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_cache(cache: Dict):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _to_cache_dict(result: SemanticClassification) -> Dict:
    return {
        "author_is_beginner": result.author_is_beginner,
        "targets_beginners": result.targets_beginners,
        "decision_dependence": result.decision_dependence,
        "basic_knowledge_gap": result.basic_knowledge_gap,
        "fomo_or_panic": result.fomo_or_panic,
        "investment_intent": result.investment_intent,
        "spam_or_marketing": result.spam_or_marketing,
        "professional_depth": result.professional_depth,
        "confidence": result.confidence,
        "evidence": result.evidence,
    }


def _is_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _openrouter_attempts() -> int:
    try:
        return max(1, int(os.environ.get("MOM_INDEX_OPENROUTER_ATTEMPTS", DEFAULT_OPENROUTER_ATTEMPTS)))
    except ValueError:
        return DEFAULT_OPENROUTER_ATTEMPTS


def build_semantic_prompt(post: Dict, sector: str) -> str:
    title = post.get("title", "") or ""
    content = post.get("content", "") or ""
    return f"""
请分析以下简体中文零售投资社区帖子。

核心区分：
- author_is_beginner 表示作者本人是小白：作者亲自表现出基础知识不足、依赖他人替自己决策，或以新手方式困惑和反应。
- targets_beginners 表示内容面向小白：内容写给新手阅读，但作者可能是教育者、有经验的投资者或营销人员。
- 教程、总结、转载、引用别人的新手问题、反问、玩梗或营销话术，本身都不能证明作者是小白。必须依据作者本人的表达立场和上下文评分。
- 证据不足、作者身份不清或语气有歧义时，应降低 confidence，不要虚构背景。

只返回一个合法 JSON 对象，字段要求如下：
- author_is_beginner、targets_beginners、decision_dependence、basic_knowledge_gap、spam_or_marketing、professional_depth、confidence：0 到 100 的数字。
- fomo_or_panic：-100 到 100 的数字；-100 表示极度恐慌，100 表示极度追涨或贪婪。
- investment_intent：只能是 buy、sell、hold、unknown 之一。
- evidence：简短数组，每一项必须逐字摘自帖子原文。

以下示例只用于说明分类边界：

示例帖子：请问亏8%要涨多少才能回本？
示例 JSON：{{"author_is_beginner": 95, "targets_beginners": 5, "decision_dependence": 75, "basic_knowledge_gap": 95, "fomo_or_panic": -30, "investment_intent": "hold", "spam_or_marketing": 0, "professional_depth": 0, "confidence": 95, "evidence": ["请问", "亏8%", "涨多少才能回本"]}}

示例帖子：新手买美股？看这篇就够了
示例 JSON：{{"author_is_beginner": 5, "targets_beginners": 95, "decision_dependence": 0, "basic_knowledge_gap": 0, "fomo_or_panic": 0, "investment_intent": "unknown", "spam_or_marketing": 10, "professional_depth": 40, "confidence": 90, "evidence": ["新手买美股", "看这篇就够了"]}}

示例帖子：小白无脑定投攻略，评论区领取资料
示例 JSON：{{"author_is_beginner": 5, "targets_beginners": 95, "decision_dependence": 0, "basic_knowledge_gap": 0, "fomo_or_panic": 20, "investment_intent": "buy", "spam_or_marketing": 95, "professional_depth": 10, "confidence": 95, "evidence": ["小白", "无脑定投攻略", "评论区领取资料"]}}

现在分析真实帖子：
板块：{sector}
标题：{title}
正文：{content}
""".strip()


def build_openrouter_payload(post: Dict, sector: str) -> Dict:
    return {
        "model": os.environ.get("MOM_INDEX_SEMANTIC_MODEL", DEFAULT_REMOTE_MODEL),
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个严格的 JSON 分类器，负责分析简体中文零售投资社区帖子。"
                    "只返回一个合法 JSON 对象，不要使用 Markdown 代码块，不要输出解释，"
                    "也不要增加指定字段以外的字段。"
                ),
            },
            {"role": "user", "content": build_semantic_prompt(post, sector)},
        ],
    }


def parse_semantic_response(text: str) -> SemanticClassification:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    return SemanticClassification(
        author_is_beginner=data.get("author_is_beginner", 0),
        targets_beginners=data.get("targets_beginners", 0),
        decision_dependence=data.get("decision_dependence", 0),
        basic_knowledge_gap=data.get("basic_knowledge_gap", 0),
        fomo_or_panic=data.get("fomo_or_panic", 0),
        investment_intent=data.get("investment_intent", "unknown"),
        spam_or_marketing=data.get("spam_or_marketing", 0),
        professional_depth=data.get("professional_depth", 0),
        confidence=data.get("confidence", 0),
        evidence=data.get("evidence", []),
    )


def classify_semantic(post: Dict, sector: str) -> SemanticClassification:
    provider = os.environ.get("MOM_INDEX_SEMANTIC_PROVIDER", "fallback").lower()
    llm_only = _is_enabled("MOM_INDEX_LLM_ONLY")
    if llm_only and provider != "openrouter":
        raise RuntimeError("MOM_INDEX_LLM_ONLY requires MOM_INDEX_SEMANTIC_PROVIDER=openrouter")
    if llm_only and not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("MOM_INDEX_LLM_ONLY requires OPENROUTER_API_KEY")

    if (
        provider == "openrouter"
        and os.environ.get("OPENROUTER_API_KEY")
    ):
        key = _cache_key(post, sector)
        cache = _read_cache()
        if key in cache:
            return parse_semantic_response(json.dumps(cache[key], ensure_ascii=False))
        last_error = None
        for attempt in range(_openrouter_attempts()):
            try:
                response = requests.post(
                    OPENROUTER_API_URL,
                    headers={
                        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": os.environ.get("MOM_INDEX_SITE_URL", "https://marc-ko.github.io/mom-index/"),
                        "X-OpenRouter-Title": os.environ.get("MOM_INDEX_APP_TITLE", "Mom Index"),
                    },
                    data=json.dumps(build_openrouter_payload(post, sector), ensure_ascii=False).encode("utf-8"),
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                text = payload["choices"][0]["message"]["content"]
                result = parse_semantic_response(text)
                cache[key] = _to_cache_dict(result)
                _write_cache(cache)
                return result
            except MALFORMED_RESPONSE_ERRORS as exc:
                last_error = exc
                if attempt < _openrouter_attempts() - 1:
                    continue
            except Exception as exc:
                last_error = exc
                break
        if llm_only:
            raise RuntimeError(f"OpenRouter semantic classifier failed in LLM-only mode: {last_error}") from last_error
        print(f"  semantic OpenRouter classifier fallback: {last_error}")

    return classify_semantic_fallback(post, sector)


def classify_semantic_fallback(post: Dict, sector: str) -> SemanticClassification:
    title = post.get("title", "") or ""
    content = post.get("content", "") or ""
    text = f"{title} {content}".strip()
    is_question = bool(re.search(r"[?？吗呢]$", title)) or _count(text, QUESTION_WORDS) > 0
    guide_count = _count(text, GUIDE_WORDS)
    beginner_count = _count(text, BEGINNER_WORDS)
    marketing_count = _count(text, MARKETING_WORDS)
    decision_count = _count(text, DECISION_WORDS)
    basic_count = _count(text, BASIC_GAP_WORDS)
    pro_count = _count(text, PRO_WORDS)
    buy_count = _count(text, BUY_WORDS)
    sell_count = _count(text, SELL_WORDS)
    panic_count = _count(text, PANIC_WORDS)
    fomo_count = _count(text, FOMO_WORDS)

    author_is_beginner = min(100, beginner_count * 25 + int(is_question) * 25 + basic_count * 25 + decision_count * 15)
    if guide_count and not is_question:
        author_is_beginner = max(0, author_is_beginner - 45)

    targets_beginners = min(100, guide_count * 50 + beginner_count * 25)
    decision_dependence = min(100, decision_count * 45 + int(is_question) * 20)
    basic_knowledge_gap = min(100, basic_count * 50 + _count(text, QUESTION_WORDS) * 20)
    spam_or_marketing = min(100, marketing_count * 35 + max(0, guide_count - 1) * 15)
    professional_depth = min(100, pro_count * 30)

    fomo_or_panic = min(100, fomo_count * 35 + buy_count * 10) - min(100, panic_count * 35 + sell_count * 10)
    investment_intent = "unknown"
    if buy_count > sell_count:
        investment_intent = "buy"
    elif sell_count > buy_count:
        investment_intent = "sell"
    elif decision_count or is_question:
        investment_intent = "hold"

    evidence = []
    for phrase in [*BEGINNER_WORDS, *QUESTION_WORDS, *DECISION_WORDS, *BASIC_GAP_WORDS, *GUIDE_WORDS, *MARKETING_WORDS]:
        if phrase.lower() in text.lower():
            evidence.append(phrase)

    return SemanticClassification(
        author_is_beginner=author_is_beginner,
        targets_beginners=targets_beginners,
        decision_dependence=decision_dependence,
        basic_knowledge_gap=basic_knowledge_gap,
        fomo_or_panic=fomo_or_panic,
        investment_intent=investment_intent,
        spam_or_marketing=spam_or_marketing,
        professional_depth=professional_depth,
        confidence=65 if text else 0,
        evidence=evidence[:5],
    )
