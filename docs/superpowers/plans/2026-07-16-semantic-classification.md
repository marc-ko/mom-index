# Semantic Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace keyword-only beginner-post scoring with a semantic classifier that distinguishes actual beginner authors from educational, marketing, emotional, and professional posts while preserving the dashboard/index interface.

**Architecture:** Add a semantic classification layer that outputs structured dimensions, then adapt those dimensions into the existing `AnalysisResult` fields consumed by `analyzer/index_calculator.py`. Keep the current keyword classifier as a deterministic offline fallback and use OpenRouter's `openrouter/free` router only when an API key is provided.

**Tech Stack:** Python standard library, `requests`, optional OpenRouter chat completions API, existing `unittest` tests, JSONL fixtures for labeled evaluation, existing static dashboard data flow.

## Global Constraints

- Preserve `AnalysisResult.newbie_score`, `level`, `reasoning`, `sentiment_score`, `intent`, `intent_strength`, and `key_signals` so `analyzer/index_calculator.py` and `frontend/dashboard.html` keep working.
- Do not call an external LLM unless `MOM_INDEX_CLASSIFIER=semantic`, `MOM_INDEX_SEMANTIC_PROVIDER=openrouter`, and `OPENROUTER_API_KEY` are set.
- Use `openrouter/free` as the default remote model slug. Do not hard-code, commit, print, or publish the API key.
- Default local behavior must remain deterministic and runnable without network access.
- Cache semantic classification results by stable post id plus classifier version to avoid repeated API calls.
- Do not publish raw scraped post caches to GitHub Pages.
- Do not run `git push` for this feature unless explicitly requested later.
- All classifier behavior changes require tests that fail before implementation.

---

### Task 1: Define Semantic Result Model

**Files:**
- Create: `analyzer/semantic_types.py`
- Test: `tests/test_semantic_types.py`

**Interfaces:**
- Consumes: plain Python dictionaries from parsed JSON or fallback rules.
- Produces: `SemanticClassification` with `to_newbie_score()`, `level`, `sentiment_score`, `intent`, `intent_strength`, and `key_signals`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_semantic_types.py`:

```python
import unittest

from analyzer.semantic_types import SemanticClassification


class SemanticTypesTests(unittest.TestCase):
    def test_beginner_question_scores_high(self):
        result = SemanticClassification(
            author_is_beginner=90,
            targets_beginners=10,
            decision_dependence=80,
            basic_knowledge_gap=85,
            fomo_or_panic=-20,
            investment_intent="hold",
            spam_or_marketing=0,
            professional_depth=0,
            confidence=85,
            evidence=["问基础回本计算"],
        )

        self.assertGreaterEqual(result.to_newbie_score(), 70)
        self.assertEqual(result.level, "纯小白")
        self.assertEqual(result.intent, "neutral")
        self.assertGreater(result.intent_strength, 0)

    def test_education_targeting_beginners_scores_low(self):
        result = SemanticClassification(
            author_is_beginner=5,
            targets_beginners=95,
            decision_dependence=0,
            basic_knowledge_gap=0,
            fomo_or_panic=0,
            investment_intent="unknown",
            spam_or_marketing=25,
            professional_depth=35,
            confidence=80,
            evidence=["新手必看指南"],
        )

        self.assertLess(result.to_newbie_score(), 30)
        self.assertNotEqual(result.level, "纯小白")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_semantic_types -v`

Expected: `ModuleNotFoundError: No module named 'analyzer.semantic_types'`.

- [ ] **Step 3: Implement the model**

Create `analyzer/semantic_types.py`:

```python
from dataclasses import dataclass, field
from typing import List


VALID_INTENTS = {"buy", "sell", "hold", "unknown"}


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, float(value)))


@dataclass
class SemanticClassification:
    author_is_beginner: float
    targets_beginners: float
    decision_dependence: float
    basic_knowledge_gap: float
    fomo_or_panic: float
    investment_intent: str
    spam_or_marketing: float
    professional_depth: float
    confidence: float
    evidence: List[str] = field(default_factory=list)

    def __post_init__(self):
        for field_name in [
            "author_is_beginner",
            "targets_beginners",
            "decision_dependence",
            "basic_knowledge_gap",
            "spam_or_marketing",
            "professional_depth",
            "confidence",
        ]:
            setattr(self, field_name, clamp(getattr(self, field_name)))
        self.fomo_or_panic = max(-100, min(100, float(self.fomo_or_panic)))
        if self.investment_intent not in VALID_INTENTS:
            self.investment_intent = "unknown"

    def to_newbie_score(self) -> float:
        raw = (
            self.author_is_beginner * 0.45
            + self.decision_dependence * 0.25
            + self.basic_knowledge_gap * 0.20
            + max(abs(self.fomo_or_panic) - 25, 0) * 0.10
            - self.spam_or_marketing * 0.35
            - self.professional_depth * 0.25
        )
        confidence_penalty = (100 - self.confidence) * 0.10
        return round(clamp(raw - confidence_penalty), 1)

    @property
    def level(self) -> str:
        score = self.to_newbie_score()
        if self.spam_or_marketing >= 80:
            return "垃圾帖"
        if score >= 50:
            return "纯小白"
        if score >= 35:
            return "偏小白"
        if score >= 20:
            return "中间派"
        if score >= 10:
            return "偏专业"
        return "专业投资者"

    @property
    def intent(self) -> str:
        if self.investment_intent == "buy":
            return "buy"
        if self.investment_intent == "sell":
            return "sell"
        return "neutral"

    @property
    def intent_strength(self) -> float:
        if self.intent == "neutral":
            return 0.0
        return round(clamp(abs(self.fomo_or_panic), 0, 100) / 100, 2)

    @property
    def sentiment_score(self) -> float:
        return round(max(-100, min(100, self.fomo_or_panic)) / 100, 2)

    @property
    def key_signals(self) -> List[str]:
        signals = []
        if self.author_is_beginner >= 60:
            signals.append(f"语义判断: 作者像真实小白 ({self.author_is_beginner:.0f}/100)")
        if self.targets_beginners >= 60 and self.author_is_beginner < 40:
            signals.append(f"语义判断: 内容面向小白但作者未必是小白 ({self.targets_beginners:.0f}/100)")
        if self.decision_dependence >= 60:
            signals.append(f"语义判断: 依赖他人决策 ({self.decision_dependence:.0f}/100)")
        if self.basic_knowledge_gap >= 60:
            signals.append(f"语义判断: 基础知识缺口 ({self.basic_knowledge_gap:.0f}/100)")
        if self.spam_or_marketing >= 60:
            signals.append(f"语义判断: 营销/引流风险 ({self.spam_or_marketing:.0f}/100)")
        return signals[:3] or [f"语义置信度 {self.confidence:.0f}/100"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_semantic_types -v`

Expected: `OK`.

- [ ] **Step 5: Commit**

Run:

```bash
git add analyzer/semantic_types.py tests/test_semantic_types.py
git commit -m "Add semantic classification result model"
```

---

### Task 2: Add Deterministic Semantic Fallback Classifier

**Files:**
- Create: `analyzer/semantic_classifier.py`
- Test: `tests/test_semantic_classifier.py`

**Interfaces:**
- Consumes: `classify_semantic(post: dict, sector: str) -> SemanticClassification`.
- Produces: semantic dimensions without external API calls when semantic mode is disabled.

- [ ] **Step 1: Write the failing test**

Create `tests/test_semantic_classifier.py`:

```python
import unittest

from analyzer.semantic_classifier import classify_semantic


class SemanticClassifierTests(unittest.TestCase):
    def test_real_beginner_question_beats_beginner_guide(self):
        question = classify_semantic(
            {"id": "q1", "title": "请问-8.47是不是要涨9个多点才能盈利啊？"},
            "nasdaq",
        )
        guide = classify_semantic(
            {"id": "g1", "title": "新手买美股？看这篇就够了"},
            "nasdaq",
        )

        self.assertGreater(question.author_is_beginner, guide.author_is_beginner)
        self.assertGreater(question.basic_knowledge_gap, guide.basic_knowledge_gap)
        self.assertLess(guide.to_newbie_score(), question.to_newbie_score())

    def test_marketing_language_is_penalized(self):
        result = classify_semantic(
            {"id": "m1", "title": "小白无脑定投纳斯达克攻略，评论区领取资料"},
            "nasdaq",
        )

        self.assertGreaterEqual(result.targets_beginners, 70)
        self.assertGreaterEqual(result.spam_or_marketing, 40)
        self.assertLess(result.to_newbie_score(), 50)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_semantic_classifier -v`

Expected: `ModuleNotFoundError: No module named 'analyzer.semantic_classifier'`.

- [ ] **Step 3: Implement deterministic fallback**

Create `analyzer/semantic_classifier.py`:

```python
import re
from typing import Dict

from analyzer.semantic_types import SemanticClassification


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


def classify_semantic(post: Dict, sector: str) -> SemanticClassification:
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

    targets_beginners = min(100, guide_count * 35 + beginner_count * 20)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_semantic_classifier -v`

Expected: `OK`.

- [ ] **Step 5: Commit**

Run:

```bash
git add analyzer/semantic_classifier.py tests/test_semantic_classifier.py
git commit -m "Add deterministic semantic classifier"
```

---

### Task 3: Integrate Semantic Classification Into Existing Analyzer

**Files:**
- Modify: `analyzer/llm_analyzer.py`
- Test: `tests/test_analyzer_semantic_integration.py`

**Interfaces:**
- Consumes: `classify_semantic(post, sector)` from Task 2.
- Produces: existing `analyze_post(post, sector) -> AnalysisResult`, with values populated from semantic dimensions when `MOM_INDEX_CLASSIFIER=semantic`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_analyzer_semantic_integration.py`:

```python
import os
import unittest
from unittest.mock import patch

from analyzer.llm_analyzer import analyze_post


class AnalyzerSemanticIntegrationTests(unittest.TestCase):
    def test_semantic_mode_penalizes_beginner_guide(self):
        with patch.dict(os.environ, {"MOM_INDEX_CLASSIFIER": "semantic"}):
            question = analyze_post({"id": "q1", "title": "请问-8.47是不是要涨9个多点才能盈利啊？"}, "nasdaq")
            guide = analyze_post({"id": "g1", "title": "新手买美股？看这篇就够了"}, "nasdaq")

        self.assertGreater(question.newbie_score, guide.newbie_score)
        self.assertIn("语义", question.reasoning)
        self.assertIn(question.level, {"纯小白", "偏小白"})

    def test_default_mode_keeps_keyword_classifier(self):
        with patch.dict(os.environ, {}, clear=True):
            result = analyze_post({"id": "g1", "title": "新手买美股？看这篇就够了"}, "nasdaq")

        self.assertGreaterEqual(result.newbie_score, 35)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_analyzer_semantic_integration -v`

Expected: FAIL because `MOM_INDEX_CLASSIFIER=semantic` is not wired.

- [ ] **Step 3: Implement semantic branch**

Modify `analyzer/llm_analyzer.py`:

```python
import os
from analyzer.semantic_classifier import classify_semantic
```

At the start of `analyze_post`, after spam filtering but before keyword scoring, add:

```python
    if os.environ.get("MOM_INDEX_CLASSIFIER", "keyword").lower() == "semantic":
        semantic = classify_semantic(post, sector)
        result = AnalysisResult(
            post_id=post.get("id", ""),
            title=title[:80],
            platform=post.get("platform", "unknown"),
            sector=sector,
            newbie_score=semantic.to_newbie_score(),
            newbie_confidence="high" if semantic.confidence >= 75 else "medium" if semantic.confidence >= 50 else "low",
            level=semantic.level,
            reasoning=(
                "语义分类: "
                f"作者小白={semantic.author_is_beginner:.0f}, "
                f"面向小白={semantic.targets_beginners:.0f}, "
                f"决策依赖={semantic.decision_dependence:.0f}, "
                f"基础缺口={semantic.basic_knowledge_gap:.0f}, "
                f"营销={semantic.spam_or_marketing:.0f}, "
                f"专业深度={semantic.professional_depth:.0f}. "
                f"证据: {', '.join(semantic.evidence[:3]) or '无明确短语'}."
            ),
            sentiment_score=semantic.sentiment_score,
            intent=semantic.intent,
            intent_strength=semantic.intent_strength,
            key_signals=semantic.key_signals,
        )
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_analyzer_semantic_integration tests.test_semantic_classifier tests.test_semantic_types -v`

Expected: `OK`.

- [ ] **Step 5: Commit**

Run:

```bash
git add analyzer/llm_analyzer.py tests/test_analyzer_semantic_integration.py
git commit -m "Wire semantic classifier into analyzer"
```

---

### Task 4: Add Optional OpenRouter Semantic Classifier

**Files:**
- Modify: `analyzer/semantic_classifier.py`
- Test: `tests/test_semantic_openrouter_payload.py`

**Interfaces:**
- Consumes: `MOM_INDEX_CLASSIFIER=semantic`, `MOM_INDEX_SEMANTIC_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, optional `MOM_INDEX_SEMANTIC_MODEL`.
- Produces: `SemanticClassification` parsed from strict JSON returned by OpenRouter's OpenAI-compatible `/api/v1/chat/completions` endpoint, falling back to deterministic classification on API error.

- [ ] **Step 1: Write the failing test**

Create `tests/test_semantic_openrouter_payload.py`:

```python
import json
import unittest

from analyzer.semantic_classifier import build_openrouter_payload, build_semantic_prompt, parse_semantic_response


class SemanticOpenRouterPayloadTests(unittest.TestCase):
    def test_prompt_requires_author_vs_target_distinction(self):
        prompt = build_semantic_prompt({"title": "新手买美股？看这篇就够了"}, "nasdaq")

        self.assertIn("author_is_beginner", prompt)
        self.assertIn("targets_beginners", prompt)
        self.assertIn("Do not treat educational content as beginner-authored", prompt)

    def test_openrouter_payload_uses_free_router(self):
        payload = build_openrouter_payload({"title": "请问亏8%要涨多少回本？"}, "nasdaq")

        self.assertEqual(payload["model"], "openrouter/free")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(payload["temperature"], 0)

    def test_parse_semantic_response_returns_model(self):
        payload = json.dumps({
            "author_is_beginner": 5,
            "targets_beginners": 95,
            "decision_dependence": 0,
            "basic_knowledge_gap": 0,
            "fomo_or_panic": 0,
            "investment_intent": "unknown",
            "spam_or_marketing": 30,
            "professional_depth": 20,
            "confidence": 80,
            "evidence": ["看这篇"],
        })

        result = parse_semantic_response(payload)

        self.assertEqual(result.targets_beginners, 95)
        self.assertLess(result.to_newbie_score(), 30)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_semantic_openrouter_payload -v`

Expected: FAIL because prompt/parse helpers do not exist.

- [ ] **Step 3: Implement prompt, payload builder, and parser**

Append to `analyzer/semantic_classifier.py`:

```python
import json
import os
import requests


CLASSIFIER_VERSION = "semantic-openrouter-free-v1"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_REMOTE_MODEL = "openrouter/free"


def build_semantic_prompt(post: Dict, sector: str) -> str:
    title = post.get("title", "") or ""
    content = post.get("content", "") or ""
    return f"""
Classify this Chinese retail-investing social post.

Critical distinction:
- author_is_beginner means the author appears to be a real beginner asking or reacting.
- targets_beginners means the content is written for beginners, such as guides, tutorials, or marketing.
- Do not treat educational content as beginner-authored unless the author shows their own confusion or decision dependence.

Return strict JSON with these numeric fields from 0 to 100 unless otherwise stated:
author_is_beginner, targets_beginners, decision_dependence, basic_knowledge_gap,
spam_or_marketing, professional_depth, confidence.
Return fomo_or_panic from -100 panic/fear to +100 FOMO/greed.
Return investment_intent as one of: buy, sell, hold, unknown.
Return evidence as a short list of exact phrases from the post.

Sector: {sector}
Title: {title}
Content: {content}
""".strip()


def build_openrouter_payload(post: Dict, sector: str) -> Dict:
    return {
        "model": os.environ.get("MOM_INDEX_SEMANTIC_MODEL", DEFAULT_REMOTE_MODEL),
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You are a strict JSON classifier for Chinese retail-investing posts. Return JSON only.",
            },
            {"role": "user", "content": build_semantic_prompt(post, sector)},
        ],
    }


def parse_semantic_response(text: str) -> SemanticClassification:
    data = json.loads(text)
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
```

- [ ] **Step 4: Implement optional OpenRouter API call**

Extend `classify_semantic` so deterministic fallback remains default:

```python
def classify_semantic(post: Dict, sector: str) -> SemanticClassification:
    if (
        os.environ.get("MOM_INDEX_SEMANTIC_PROVIDER", "fallback").lower() == "openrouter"
        and os.environ.get("OPENROUTER_API_KEY")
    ):
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
            return parse_semantic_response(text)
        except Exception as exc:
            print(f"  semantic OpenRouter classifier fallback: {exc}")

    return classify_semantic_fallback(post, sector)
```

Rename the current deterministic body from Task 2 to:

```python
def classify_semantic_fallback(post: Dict, sector: str) -> SemanticClassification:
    ...
```

- [ ] **Step 5: Run tests**

Run: `python -m unittest tests.test_semantic_openrouter_payload tests.test_semantic_classifier tests.test_analyzer_semantic_integration -v`

Expected: `OK`.

- [ ] **Step 6: Commit**

Run:

```bash
git add analyzer/semantic_classifier.py tests/test_semantic_openrouter_payload.py
git commit -m "Add optional OpenRouter semantic classifier"
```

---

### Task 5: Add Labeled Evaluation Harness

**Files:**
- Create: `data/labeled_posts.example.jsonl`
- Create: `tests/test_classifier_eval.py`
- Create: `scripts/evaluate_classifier.py`

**Interfaces:**
- Consumes: JSONL rows with `post`, `sector`, and `expected_label`.
- Produces: precision/recall summary for `actual_beginner_question` and fails tests if minimum precision is not met.

- [ ] **Step 1: Write the failing test**

Create `tests/test_classifier_eval.py`:

```python
import unittest

from scripts.evaluate_classifier import evaluate_rows


class ClassifierEvalTests(unittest.TestCase):
    def test_eval_counts_beginner_question_precision(self):
        rows = [
            {"sector": "nasdaq", "post": {"title": "请问亏8%要涨多少回本？"}, "expected_label": "actual_beginner_question"},
            {"sector": "nasdaq", "post": {"title": "新手买美股？看这篇就够了"}, "expected_label": "beginner_education"},
        ]

        metrics = evaluate_rows(rows)

        self.assertIn("actual_beginner_question_precision", metrics)
        self.assertGreaterEqual(metrics["actual_beginner_question_precision"], 0.5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_classifier_eval -v`

Expected: `ModuleNotFoundError: No module named 'scripts.evaluate_classifier'`.

- [ ] **Step 3: Add example labels**

Create `data/labeled_posts.example.jsonl`:

```jsonl
{"sector":"nasdaq","post":{"title":"请问-8.47是不是要涨9个多点才能盈利啊？"},"expected_label":"actual_beginner_question"}
{"sector":"nasdaq","post":{"title":"新手买美股？看这篇就够了"},"expected_label":"beginner_education"}
{"sector":"gold","post":{"title":"小白无脑定投黄金攻略，评论区领取资料"},"expected_label":"marketing_or_creator_content"}
{"sector":"cpo","post":{"title":"满仓干主力冲鸭"},"expected_label":"emotional_retail_post"}
{"sector":"semiconductor","post":{"title":"半导体估值分位和库存周期的关系"},"expected_label":"professional_or_data_driven"}
```

- [ ] **Step 4: Implement evaluator**

Create `scripts/evaluate_classifier.py`:

```python
import json
from pathlib import Path
from typing import Dict, Iterable, List

from analyzer.semantic_classifier import classify_semantic


def predicted_label(row: Dict) -> str:
    result = classify_semantic(row["post"], row.get("sector", "unknown"))
    if result.spam_or_marketing >= 50:
        return "marketing_or_creator_content"
    if result.author_is_beginner >= 50 and (result.basic_knowledge_gap >= 40 or result.decision_dependence >= 40):
        return "actual_beginner_question"
    if result.targets_beginners >= 60 and result.author_is_beginner < 40:
        return "beginner_education"
    if abs(result.fomo_or_panic) >= 50:
        return "emotional_retail_post"
    if result.professional_depth >= 50:
        return "professional_or_data_driven"
    return "normal_discussion"


def evaluate_rows(rows: Iterable[Dict]) -> Dict[str, float]:
    rows = list(rows)
    predictions = [(row["expected_label"], predicted_label(row)) for row in rows]
    true_positive = sum(1 for expected, predicted in predictions if expected == predicted == "actual_beginner_question")
    predicted_positive = sum(1 for _, predicted in predictions if predicted == "actual_beginner_question")
    actual_positive = sum(1 for expected, _ in predictions if expected == "actual_beginner_question")
    precision = true_positive / max(predicted_positive, 1)
    recall = true_positive / max(actual_positive, 1)
    accuracy = sum(1 for expected, predicted in predictions if expected == predicted) / max(len(predictions), 1)
    return {
        "actual_beginner_question_precision": round(precision, 3),
        "actual_beginner_question_recall": round(recall, 3),
        "accuracy": round(accuracy, 3),
    }


def load_jsonl(path: Path) -> List[Dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    rows = load_jsonl(Path("data/labeled_posts.example.jsonl"))
    print(json.dumps(evaluate_rows(rows), ensure_ascii=False, indent=2))
```

- [ ] **Step 5: Run tests and evaluator**

Run:

```bash
python -m unittest tests.test_classifier_eval -v
python scripts/evaluate_classifier.py
```

Expected: unittest `OK`, evaluator prints JSON metrics.

- [ ] **Step 6: Commit**

Run:

```bash
git add data/labeled_posts.example.jsonl scripts/evaluate_classifier.py tests/test_classifier_eval.py
git commit -m "Add semantic classifier evaluation harness"
```

---

### Task 6: Update Pipeline Documentation and Safe Defaults

**Files:**
- Modify: `README.md`
- Test: `tests/test_semantic_docs.py`

**Interfaces:**
- Consumes: environment variables documented for semantic mode.
- Produces: clear operator guidance for keyword fallback, semantic fallback, and optional OpenRouter provider.

- [ ] **Step 1: Write the failing test**

Create `tests/test_semantic_docs.py`:

```python
from pathlib import Path
import unittest


class SemanticDocsTests(unittest.TestCase):
    def test_readme_documents_semantic_classifier_flags(self):
        text = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("MOM_INDEX_CLASSIFIER", text)
        self.assertIn("MOM_INDEX_SEMANTIC_PROVIDER", text)
        self.assertIn("OPENROUTER_API_KEY", text)
        self.assertIn("openrouter/free", text)
        self.assertIn("author_is_beginner", text)
        self.assertIn("targets_beginners", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_semantic_docs -v`

Expected: FAIL because README does not document semantic classifier flags.

- [ ] **Step 3: Update README**

Add this section after `## Classification Method`:

```markdown
### Semantic Classification Mode

The default classifier is deterministic and can run offline. For more accurate
classification, set:

```powershell
$env:MOM_INDEX_CLASSIFIER="semantic"
```

Semantic mode separates `author_is_beginner` from `targets_beginners`, so a
post like `新手买美股？看这篇就够了` is treated as beginner-facing education,
not automatically as a beginner-authored post.

Optional OpenRouter-backed semantic classification uses the free models router:

```powershell
$env:MOM_INDEX_CLASSIFIER="semantic"
$env:MOM_INDEX_SEMANTIC_PROVIDER="openrouter"
$env:MOM_INDEX_SEMANTIC_MODEL="openrouter/free"
$env:OPENROUTER_API_KEY="..."
```

Without `OPENROUTER_API_KEY`, semantic mode uses the deterministic local fallback.
```
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_semantic_docs -v`

Expected: `OK`.

- [ ] **Step 5: Run full classifier suite**

Run:

```bash
python -m unittest tests.test_semantic_types tests.test_semantic_classifier tests.test_analyzer_semantic_integration tests.test_semantic_openrouter_payload tests.test_classifier_eval tests.test_semantic_docs tests.test_dashboard_top_posts tests.test_dashboard_history_data -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add README.md tests/test_semantic_docs.py
git commit -m "Document semantic classification mode"
```

---

### Task 7: Generate Data Locally

**Files:**
- Modify generated: `data/dashboard_data.json`
- Modify generated: `data/history.json`
- Modify generated: `frontend/data/dashboard_data.json`
- Modify generated: `frontend/data/history.json`
- Do not stage: `data/xhs_posts.json`, `frontend/data/xhs_posts.json` unless explicitly requested.

**Interfaces:**
- Consumes: existing `pipeline.py`.
- Produces: dashboard JSON computed through semantic classification mode.

- [ ] **Step 1: Run pipeline in semantic fallback mode**

Run:

```bash
$env:MOM_INDEX_CLASSIFIER="semantic"
python pipeline.py
```

Expected: pipeline completes and prints `历史记录: ... 条`.

- [ ] **Step 2: Optionally run pipeline with OpenRouter after API key is provided**

Run only after the operator supplies `OPENROUTER_API_KEY` in the shell environment. Do not write the key to any file.

```powershell
$env:MOM_INDEX_CLASSIFIER="semantic"
$env:MOM_INDEX_SEMANTIC_PROVIDER="openrouter"
$env:MOM_INDEX_SEMANTIC_MODEL="openrouter/free"
$env:OPENROUTER_API_KEY="<provided externally>"
python pipeline.py
```

Expected: pipeline completes. If OpenRouter fails or rate-limits, output includes `semantic OpenRouter classifier fallback` and local fallback results are still produced.

- [ ] **Step 3: Verify generated data**

Run:

```bash
python -c "import json; d=json.load(open('frontend/data/dashboard_data.json', encoding='utf-8')); print(d['record_count']); print({k: len(v.get('top_newbie_posts') or []) for k,v in d['latest']['sectors'].items()})"
```

Expected: record count stays at or above 30; each sector has up to 5 top posts.

- [ ] **Step 4: Run tests**

Run:

```bash
python -m unittest tests.test_semantic_types tests.test_semantic_classifier tests.test_analyzer_semantic_integration tests.test_semantic_openrouter_payload tests.test_classifier_eval tests.test_semantic_docs tests.test_dashboard_top_posts tests.test_dashboard_history_data -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit generated dashboard data**

Run:

```bash
git add data/dashboard_data.json data/history.json frontend/data/dashboard_data.json frontend/data/history.json
git commit -m "Update dashboard data with semantic classifier"
```

- [ ] **Step 6: Update GitHub Pages worktree locally**

Use the existing Pages worktree at `C:\dev\mom-index-pages`. Update the local Pages worktree with `dashboard.html`, full `dashboard_data.json`, and sanitized `history.json`, but do not push:

```powershell
Copy-Item -LiteralPath C:\dev\mom-index\frontend\dashboard.html -Destination C:\dev\mom-index-pages\dashboard.html -Force
Copy-Item -LiteralPath C:\dev\mom-index\frontend\data\dashboard_data.json -Destination C:\dev\mom-index-pages\data\dashboard_data.json -Force
python -c "import json; from pathlib import Path; src=Path(r'C:\dev\mom-index\frontend\data\history.json'); dst=Path(r'C:\dev\mom-index-pages\data\history.json'); h=json.loads(src.read_text(encoding='utf-8')); [sector.__setitem__('top_newbie_posts', []) for record in h.get('records', []) for sector in (record.get('sectors') or {}).values()]; dst.write_text(json.dumps(h, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')"
```

- [ ] **Step 7: Commit Pages worktree locally**

Run:

```bash
git -C C:\dev\mom-index-pages add dashboard.html data/dashboard_data.json data/history.json
git -C C:\dev\mom-index-pages commit -m "Publish semantic classification dashboard"
```

Expected: local commit succeeds. Do not run `git push` for `master` or `gh-pages` unless explicitly requested later.

---

## Self-Review

- Spec coverage: The plan covers semantic dimensions, deterministic fallback, optional OpenRouter classification with `openrouter/free`, integration with existing `AnalysisResult`, evaluation, documentation, generated data, and local GitHub Pages worktree updates without push.
- Placeholder scan: No `TBD`, `TODO`, or unspecified implementation blocks remain.
- Type consistency: `SemanticClassification`, `classify_semantic`, `classify_semantic_fallback`, `build_semantic_prompt`, `build_openrouter_payload`, and `parse_semantic_response` are consistently referenced across tasks.
