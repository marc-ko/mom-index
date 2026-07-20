import unittest
from unittest.mock import Mock, patch

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

    @patch("analyzer.semantic_classifier._write_cache")
    @patch("analyzer.semantic_classifier._read_cache", return_value={})
    @patch("analyzer.semantic_classifier.requests.post")
    def test_openrouter_retries_malformed_json_before_fallback(self, post, _read_cache, _write_cache):
        malformed = Mock()
        malformed.raise_for_status.return_value = None
        malformed.json.return_value = {"choices": [{"message": {"content": "not json"}}]}
        valid = Mock()
        valid.raise_for_status.return_value = None
        valid.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"author_is_beginner": 90, "targets_beginners": 5, '
                            '"decision_dependence": 80, "basic_knowledge_gap": 90, '
                            '"fomo_or_panic": -20, "investment_intent": "hold", '
                            '"spam_or_marketing": 0, "professional_depth": 0, '
                            '"confidence": 95, "evidence": ["黄金怎么买"]}'
                        )
                    }
                }
            ]
        }
        post.side_effect = [malformed, valid]

        with patch.dict(
            "os.environ",
            {
                "MOM_INDEX_SEMANTIC_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": "test-key",
            },
            clear=False,
        ):
            result = classify_semantic({"id": "retry-json", "title": "黄金怎么买"}, "gold")

        self.assertEqual(post.call_count, 2)
        self.assertEqual(result.confidence, 95)
        self.assertEqual(result.author_is_beginner, 90)

    @patch("analyzer.semantic_classifier._write_cache")
    @patch("analyzer.semantic_classifier._read_cache", return_value={})
    @patch("analyzer.semantic_classifier.requests.post")
    def test_openrouter_retries_missing_content_as_malformed_output(self, post, _read_cache, _write_cache):
        malformed = Mock()
        malformed.raise_for_status.return_value = None
        malformed.json.return_value = {"choices": [{"message": {"content": None}}]}
        valid = Mock()
        valid.raise_for_status.return_value = None
        valid.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"author_is_beginner": 80, "targets_beginners": 5, '
                            '"decision_dependence": 70, "basic_knowledge_gap": 80, '
                            '"fomo_or_panic": -30, "investment_intent": "hold", '
                            '"spam_or_marketing": 0, "professional_depth": 5, '
                            '"confidence": 90, "evidence": ["回本"]}'
                        )
                    }
                }
            ]
        }
        post.side_effect = [malformed, valid]

        with patch.dict(
            "os.environ",
            {
                "MOM_INDEX_SEMANTIC_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": "test-key",
            },
            clear=False,
        ):
            result = classify_semantic({"id": "retry-none", "title": "还能回本吗"}, "semiconductor")

        self.assertEqual(post.call_count, 2)
        self.assertEqual(result.confidence, 90)
        self.assertEqual(result.basic_knowledge_gap, 80)

    @patch("analyzer.semantic_classifier._read_cache", return_value={})
    @patch("analyzer.semantic_classifier.requests.post")
    def test_llm_only_raises_instead_of_falling_back_on_openrouter_error(self, post, _read_cache):
        error_response = Mock()
        error_response.raise_for_status.side_effect = Exception("429 too many requests")
        post.return_value = error_response

        with patch.dict(
            "os.environ",
            {
                "MOM_INDEX_SEMANTIC_PROVIDER": "openrouter",
                "MOM_INDEX_LLM_ONLY": "1",
                "OPENROUTER_API_KEY": "test-key",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                classify_semantic({"id": "llm-only-error", "title": "黄金怎么买"}, "gold")


if __name__ == "__main__":
    unittest.main()
