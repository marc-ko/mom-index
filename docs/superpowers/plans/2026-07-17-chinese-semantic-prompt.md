# Chinese Semantic Prompt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the English OpenRouter classification instructions with a Simplified Chinese prompt containing three concise contrasting examples, while preserving the existing JSON response contract.

**Architecture:** Keep prompt construction inside `analyzer/semantic_classifier.py` and keep parsing, scoring, provider selection, and fallback behavior unchanged. Lock the Chinese instructions, English JSON keys, three few-shot boundaries, and real-post interpolation into payload tests before changing production code; bump the classifier cache version so old responses do not mask the new prompt.

**Tech Stack:** Python 3, standard-library `unittest`, OpenRouter chat-completions payloads, existing `requests` integration.

## Global Constraints

- Both the system message and user prompt must be written in Simplified Chinese.
- JSON field names remain in English.
- `investment_intent` values remain `buy`, `sell`, `hold`, and `unknown`.
- Use exactly three short examples: genuine beginner question, beginner-facing guide, and beginner-facing marketing post.
- Do not change scoring, parsing, provider selection, fallback behavior, or dashboard code.
- Evidence strings in every example must be exact phrases from that example's post.
- Do not commit API keys, chat content, generated dashboard data, or unrelated working-tree changes.
- Commit locally only; do not push.

---

### Task 1: Replace the OpenRouter Prompt Contract

**Files:**
- Modify: `tests/test_semantic_openrouter_payload.py`
- Modify: `analyzer/semantic_classifier.py:12,74-109`

**Interfaces:**
- Consumes: `build_semantic_prompt(post: Dict, sector: str) -> str` and `build_openrouter_payload(post: Dict, sector: str) -> Dict`.
- Produces: the same OpenRouter payload structure and JSON response schema currently consumed by `parse_semantic_response(text: str) -> SemanticClassification`.

- [ ] **Step 1: Replace the prompt-contract tests with failing Chinese-language assertions**

Replace `tests/test_semantic_openrouter_payload.py` with:

```python
import json
import unittest

from analyzer.semantic_classifier import (
    CLASSIFIER_VERSION,
    build_openrouter_payload,
    build_semantic_prompt,
    parse_semantic_response,
)


class SemanticOpenRouterPayloadTests(unittest.TestCase):
    def test_classifier_version_invalidates_english_prompt_cache(self):
        self.assertEqual(CLASSIFIER_VERSION, "semantic-openrouter-free-v2")

    def test_prompt_uses_chinese_instructions_and_preserves_json_schema(self):
        prompt = build_semantic_prompt({"title": "新手买美股？看这篇就够了"}, "nasdaq")

        self.assertIn("请分析以下简体中文零售投资社区帖子", prompt)
        self.assertIn("作者本人是小白", prompt)
        self.assertIn("内容面向小白", prompt)
        self.assertNotIn("Classify this Chinese retail-investing social post", prompt)
        self.assertNotIn("Do not treat educational content as beginner-authored", prompt)
        for field in (
            "author_is_beginner",
            "targets_beginners",
            "decision_dependence",
            "basic_knowledge_gap",
            "fomo_or_panic",
            "investment_intent",
            "spam_or_marketing",
            "professional_depth",
            "confidence",
            "evidence",
        ):
            self.assertIn(field, prompt)
        self.assertIn("buy、sell、hold、unknown", prompt)

    def test_prompt_includes_three_contrasting_examples_and_real_post(self):
        prompt = build_semantic_prompt(
            {"title": "我现在应该割肉吗？", "content": "已经亏了15%，完全不知道怎么办。"},
            "沪深300",
        )

        self.assertEqual(prompt.count("示例帖子："), 3)
        self.assertIn("请问亏8%要涨多少才能回本？", prompt)
        self.assertIn("新手买美股？看这篇就够了", prompt)
        self.assertIn("小白无脑定投攻略，评论区领取资料", prompt)
        self.assertIn('"author_is_beginner": 95', prompt)
        self.assertIn('"targets_beginners": 95', prompt)
        self.assertIn('"spam_or_marketing": 95', prompt)
        self.assertIn("板块：沪深300", prompt)
        self.assertIn("标题：我现在应该割肉吗？", prompt)
        self.assertIn("正文：已经亏了15%，完全不知道怎么办。", prompt)

    def test_openrouter_payload_uses_chinese_system_message_and_free_router(self):
        payload = build_openrouter_payload({"title": "请问亏8%要涨多少回本？"}, "nasdaq")

        self.assertEqual(payload["model"], "openrouter/free")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(payload["temperature"], 0)
        system_message = payload["messages"][0]["content"]
        self.assertIn("简体中文零售投资社区帖子", system_message)
        self.assertIn("只返回一个合法 JSON 对象", system_message)
        self.assertNotIn("You are a strict JSON classifier", system_message)

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

- [ ] **Step 2: Run the prompt tests and verify the expected failures**

Run:

```powershell
python -m unittest tests.test_semantic_openrouter_payload -v
```

Expected: the cache-version assertion and three prompt/payload tests fail because production still uses the `v1` cache version and English instructions; `test_parse_semantic_response_returns_model` passes.

- [ ] **Step 3: Implement the Chinese prompt, three few-shot examples, and cache-version bump**

In `analyzer/semantic_classifier.py`, change:

```python
CLASSIFIER_VERSION = "semantic-openrouter-free-v1"
```

to:

```python
CLASSIFIER_VERSION = "semantic-openrouter-free-v2"
```

Replace `build_semantic_prompt()` with:

```python
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
```

In `build_openrouter_payload()`, replace the system-message content with:

```python
"content": (
    "你是一个严格的 JSON 分类器，负责分析简体中文零售投资社区帖子。"
    "只返回一个合法 JSON 对象，不要使用 Markdown 代码块，不要输出解释，"
    "也不要增加指定字段以外的字段。"
),
```

- [ ] **Step 4: Run the targeted tests and verify they pass**

Run:

```powershell
python -m unittest tests.test_semantic_openrouter_payload -v
```

Expected: `Ran 5 tests` and `OK`.

- [ ] **Step 5: Run the semantic and dashboard regression suite**

Run:

```powershell
python -m unittest tests.test_semantic_types tests.test_semantic_classifier tests.test_analyzer_semantic_integration tests.test_semantic_openrouter_payload tests.test_classifier_eval tests.test_semantic_docs tests.test_dashboard_top_posts tests.test_dashboard_history_data -v
```

Expected: all tests pass with `OK`; no network request is required.

- [ ] **Step 6: Verify scope and secret safety**

Run:

```powershell
git diff --check
git status --short
git diff -- analyzer/semantic_classifier.py tests/test_semantic_openrouter_payload.py
git diff -- analyzer/semantic_classifier.py tests/test_semantic_openrouter_payload.py | rg "OPENROUTER_API_KEY=|Bearer [A-Za-z0-9_-]{20,}"
```

Expected: `git diff --check` is silent; only the two intended implementation files are selected for the implementation commit; the secret scan prints no matches and exits with status 1. Existing unrelated generated-data and issue-template changes remain unstaged and untouched.

- [ ] **Step 7: Commit only the prompt implementation and tests**

```powershell
git add -- analyzer/semantic_classifier.py tests/test_semantic_openrouter_payload.py
git diff --cached --check
git diff --cached --name-status
git commit -m "Use Chinese semantic classifier prompt"
```

Expected: the cached diff names only `analyzer/semantic_classifier.py` and `tests/test_semantic_openrouter_payload.py`; the commit succeeds locally. Do not run `git push`.
