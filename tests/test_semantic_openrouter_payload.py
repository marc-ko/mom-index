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
