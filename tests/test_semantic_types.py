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
