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
