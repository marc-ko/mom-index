import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "create-daily-issue.yml"
RUNNER = ROOT / "scripts" / "run_daily.ps1"
INSTALLER = ROOT / "scripts" / "install_daily_task.ps1"


class DailyIssueReportTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self.data_dir = self.root / "data"
        self.github_dir = self.root / ".github"
        self.data_dir.mkdir()

        dashboard = {
            "latest": {
                "date": "2026-07-16",
                "sectors": {
                    "nasdaq": {
                        "index": 17.0,
                        "interpretation": "cold",
                        "details": {
                            "mom_buy_index": 16.4,
                            "mom_sell_index": 0.0,
                            "total_posts": 104,
                            "newbie_posts": 19,
                        },
                        "top_newbie_posts": [
                            {"title": "raw xhs post title should stay out"}
                        ],
                    },
                    "gold": {
                        "index": 16.8,
                        "interpretation": "cold",
                        "details": {
                            "mom_buy_index": 0.0,
                            "mom_sell_index": 12.2,
                            "total_posts": 93,
                            "newbie_posts": 14,
                        },
                    },
                    "cpo": {
                        "index": 23.5,
                        "interpretation": "normal",
                        "details": {
                            "mom_buy_index": 15.4,
                            "mom_sell_index": 24.8,
                            "total_posts": 96,
                            "newbie_posts": 8,
                        },
                    },
                    "semiconductor": {
                        "index": 18.5,
                        "interpretation": "cold",
                        "details": {
                            "mom_buy_index": 21.6,
                            "mom_sell_index": 0.0,
                            "total_posts": 95,
                            "newbie_posts": 15,
                        },
                    },
                },
            }
        }
        (self.data_dir / "dashboard_data.json").write_text(
            json.dumps(dashboard), encoding="utf-8"
        )

    def test_issue_template_includes_daily_sector_snapshot_without_raw_posts(self):
        from scripts.generate_issue_template import generate_issue_template

        output = self.github_dir / "ISSUE_TEMPLATE.md"
        generate_issue_template(
            dashboard_path=self.data_dir / "dashboard_data.json",
            output_path=output,
            dashboard_url="https://example.com/dashboard.html",
        )

        text = output.read_text(encoding="utf-8")
        self.assertIn("title: Mom Index Daily Report - 2026-07-16", text)
        self.assertIn("labels: documentation", text)
        self.assertIn("# Mom Index Daily Report", text)
        self.assertIn("Date: 2026-07-16", text)
        self.assertIn("https://example.com/dashboard.html", text)
        self.assertIn("| Sector | Mom Index | Mom Buy | Mom Sell | Posts | Newbie Posts | Interpretation |", text)
        for sector in ("Nasdaq", "Gold", "CPO / Communications", "Semiconductor"):
            with self.subTest(sector=sector):
                self.assertIn(sector, text)
        self.assertIn("| Nasdaq | 17.0 | 16.4 | 0.0 | 104 | 19 | cold |", text)
        self.assertIn("Raw Rednote/Xiaohongshu post text is not published", text)
        self.assertNotIn("raw xhs post title should stay out", text)

    def test_workflow_creates_issue_from_template_on_template_push(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("issues: write", workflow)
        self.assertIn(".github/ISSUE_TEMPLATE.md", workflow)
        self.assertIn("gh issue list", workflow)
        self.assertIn("gh issue create", workflow)
        self.assertIn("GITHUB_TOKEN", workflow)

    def test_daily_runner_forces_llm_only_semantic_classifier(self):
        runner = RUNNER.read_text(encoding="utf-8")

        self.assertIn('MOM_INDEX_CLASSIFIER = "semantic"', runner)
        self.assertIn('MOM_INDEX_SEMANTIC_PROVIDER = "openrouter"', runner)
        self.assertIn('MOM_INDEX_SEMANTIC_MODEL = "openrouter/free"', runner)
        self.assertIn('MOM_INDEX_LLM_ONLY = "1"', runner)
        self.assertIn("OPENROUTER_API_KEY", runner)
        self.assertIn("Pages commit failed", runner)
        self.assertIn("Pages push failed", runner)

    def test_task_installer_preserves_push_report_switch(self):
        installer = INSTALLER.read_text(encoding="utf-8")

        self.assertIn("[switch]$PushReport", installer)
        self.assertIn('$arguments += " -PushReport"', installer)


if __name__ == "__main__":
    unittest.main()
