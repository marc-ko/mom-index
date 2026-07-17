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
