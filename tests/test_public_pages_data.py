from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUN_DAILY = ROOT / "scripts" / "run_daily.ps1"


class PublicPagesDataTests(unittest.TestCase):
    def test_pages_publish_keeps_generated_top_posts(self):
        script = RUN_DAILY.read_text(encoding="utf-8")

        self.assertNotIn('sector["top_newbie_posts"] = []', script)
        self.assertNotIn("build_public_pages_data.py", script)
        self.assertIn('(Join-Path $RepoRoot "data\\dashboard_data.json")', script)
        self.assertIn('(Join-Path $RepoRoot "data\\history.json")', script)


if __name__ == "__main__":
    unittest.main()
