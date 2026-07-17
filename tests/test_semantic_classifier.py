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
