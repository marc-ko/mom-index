from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DATA = ROOT / "frontend" / "data" / "dashboard_data.json"


class DashboardHistoryDataTests(unittest.TestCase):
    def test_dashboard_keeps_full_history_series(self):
        data = json.loads(DASHBOARD_DATA.read_text(encoding="utf-8"))

        self.assertGreaterEqual(data.get("record_count", 0), 30)
        for sector, records in data.get("sector_history", {}).items():
            with self.subTest(sector=sector):
                self.assertGreaterEqual(len(records), 30)


if __name__ == "__main__":
    unittest.main()
