from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUN_DAILY = ROOT / "scripts" / "run_daily.ps1"
DASHBOARD = ROOT / "frontend" / "dashboard.html"


class PublicPagesDataTests(unittest.TestCase):
    def test_pages_publish_keeps_generated_top_posts(self):
        script = RUN_DAILY.read_text(encoding="utf-8")

        self.assertNotIn('sector["top_newbie_posts"] = []', script)
        self.assertNotIn("build_public_pages_data.py", script)
        self.assertIn('(Join-Path $RepoRoot "frontend\\dashboard.html")', script)
        self.assertIn('(Join-Path $RepoRoot "frontend\\data\\dashboard_data.json")', script)
        self.assertIn('(Join-Path $RepoRoot "frontend\\data\\history.json")', script)

    def test_live_dashboard_reads_master_repo_data_first(self):
        html = DASHBOARD.read_text(encoding="utf-8")

        self.assertIn(
            "https://raw.githubusercontent.com/marc-ko/mom-index/master/data/dashboard_data.json",
            html,
        )
        self.assertIn("window.location.hostname.endsWith('github.io')", html)
        self.assertIn("return [`${REPO_DASHBOARD_DATA_URL}?v=${Date.now()}`, localDataUrl];", html)


if __name__ == "__main__":
    unittest.main()
