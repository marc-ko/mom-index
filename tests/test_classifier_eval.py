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
