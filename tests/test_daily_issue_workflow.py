from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "create-daily-issue.yml"


class DailyIssueWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_runs_daily_at_0800_hong_kong_time(self):
        self.assertIn("schedule:", self.workflow)
        self.assertIn('cron: "0 0 * * *"', self.workflow)

    def test_can_be_run_manually(self):
        self.assertIn("workflow_dispatch:", self.workflow)

    def test_still_runs_when_daily_template_is_pushed(self):
        self.assertIn('push:', self.workflow)
        self.assertIn('".github/ISSUE_TEMPLATE.md"', self.workflow)

    def test_runs_when_dashboard_data_is_pushed(self):
        self.assertIn('".github/workflows/create-daily-issue.yml"', self.workflow)
        self.assertIn('"data/dashboard_data.json"', self.workflow)
        self.assertIn('"data/history.json"', self.workflow)
        self.assertIn('"frontend/dashboard.html"', self.workflow)

    def test_publishes_dashboard_to_gh_pages(self):
        self.assertIn("contents: write", self.workflow)
        self.assertIn("pages: write", self.workflow)
        self.assertIn("id-token: write", self.workflow)
        self.assertIn("Publish dashboard to gh-pages", self.workflow)
        self.assertIn("actions/upload-pages-artifact", self.workflow)
        self.assertIn("actions/deploy-pages", self.workflow)
        self.assertIn("path: public", self.workflow)


if __name__ == "__main__":
    unittest.main()
