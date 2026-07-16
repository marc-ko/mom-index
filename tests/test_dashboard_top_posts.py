from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "frontend" / "dashboard.html"


class DashboardTopPostsTests(unittest.TestCase):
    def setUp(self):
        self.html = DASHBOARD.read_text(encoding="utf-8")

    def test_top_posts_are_grouped_by_sector(self):
        self.assertIn("sector-post-group", self.html)
        self.assertIn("sector-post-title", self.html)
        self.assertIn("const sectorEntries = Object.entries(latest.sectors);", self.html)
        self.assertRegex(self.html, r"const topPosts = \(sdata\.top_newbie_posts \|\| \[\]\)\.slice\(0, 5\);")

    def test_top_posts_do_not_use_one_global_slice(self):
        self.assertNotIn("let allTop = [];", self.html)
        self.assertNotIn("allTop = allTop.slice", self.html)

    def test_each_sector_renders_empty_state(self):
        self.assertIn("sectorNoTopPosts", self.html)
        self.assertRegex(self.html, r"if \(!topPosts\.length\)")


if __name__ == "__main__":
    unittest.main()
