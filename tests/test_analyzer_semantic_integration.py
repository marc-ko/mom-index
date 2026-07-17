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
