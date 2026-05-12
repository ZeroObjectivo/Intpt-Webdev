import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DashboardLayoutTest(unittest.TestCase):
    def setUp(self):
        self.css = (PROJECT_ROOT / "app" / "static" / "css" / "dashboard.css").read_text()
        self.template = (PROJECT_ROOT / "app" / "templates" / "dashboard.html").read_text()

    def test_dashboard_grid_uses_fluid_columns_instead_of_rigid_widths(self):
        container_rule = re.search(r"\.dashboard-container\s*\{(?P<body>.*?)\}", self.css, re.S)

        self.assertIsNotNone(container_rule)
        rule_body = container_rule.group("body")
        self.assertIn("minmax(190px, 220px)", rule_body)
        self.assertIn("minmax(0, 1fr)", rule_body)
        self.assertIn("minmax(280px, 320px)", rule_body)
        self.assertIn("width: min(1440px, calc(100vw - 40px));", rule_body)

    def test_sidebar_stays_sticky_below_header(self):
        sidebar_rule = re.search(r"\.primary-sidebar\s*\{(?P<body>.*?)\}", self.css, re.S)

        self.assertIsNotNone(sidebar_rule)
        rule_body = sidebar_rule.group("body")
        self.assertIn("position: sticky", rule_body)
        self.assertIn("top: 112px", rule_body)
        self.assertIn("Home Feed", self.template)
        self.assertIn("Marketplace", self.template)
        self.assertIn("Events", self.template)
        self.assertIn("About", self.template)
        self.assertIn("Settings", self.template)


if __name__ == "__main__":
    unittest.main()
