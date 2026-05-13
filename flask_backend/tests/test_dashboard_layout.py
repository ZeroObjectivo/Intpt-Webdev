import re
import unittest
import os
from pathlib import Path
from datetime import datetime, timezone

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIn0."
    "test-signature",
)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


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

    def test_primary_nav_links_use_eight_pixel_radius_without_active_indicator(self):
        nav_rule = re.search(r"\.primary-nav-link\s*\{(?P<body>.*?)\}", self.css, re.S)
        active_rule = re.search(r"\.primary-nav-link\.active\s*\{(?P<body>.*?)\}", self.css, re.S)

        self.assertIsNotNone(nav_rule)
        self.assertIsNotNone(active_rule)
        self.assertIn("border-radius: 8px", nav_rule.group("body"))
        self.assertNotIn("inset 4px 0", active_rule.group("body"))
        self.assertEqual(self.template.count("primary-nav-link rounded-lg"), 5)

    def test_dashboard_category_tags_use_standard_dark_palette(self):
        post_tag_matches = re.findall(
            r"<span class=\"(?P<classes>[^\"]*post-category-tag[^\"]*)\"",
            self.template,
        )
        sidebar_tag_matches = re.findall(
            r"<span class=\"category-tag inline-flex rounded-full px-3 py-1 (?P<classes>[^\"]+)\"",
            self.template,
        )
        filter_pill_matches = re.findall(
            r"<button class=\"pill rounded-full px-3 py-1 (?P<classes>[^\"]+)\"",
            self.template,
        )

        self.assertGreaterEqual(len(post_tag_matches), 5)
        self.assertEqual(len(sidebar_tag_matches), 3)
        self.assertEqual(len(filter_pill_matches), 6)
        for class_list in post_tag_matches + sidebar_tag_matches + filter_pill_matches:
            self.assertIn("font-bold", class_list)
            self.assertIn("my-[5px]", class_list)
            self.assertNotIn("font-normal", class_list)

        self.assertEqual(len(re.findall(r"<button[^>]+data-category-tag", self.template)), 6)
        self.assertIn('aria-pressed="true"', self.template)
        self.assertEqual(self.template.count('aria-pressed="false"'), 5)
        self.assertIn("bg-[#111942] text-[#C7CDE6]", filter_pill_matches[0])
        for class_list in filter_pill_matches[1:]:
            self.assertIn("bg-[#C7CDE6] text-[#111942]", class_list)
        for class_list in post_tag_matches + sidebar_tag_matches:
            self.assertIn("bg-[#C7CDE6] text-[#111942]", class_list)

        self.assertIn(".category-pills .pill", self.css)
        self.assertIn(".category-pills .pill.active", self.css)
        self.assertIn(".category-tag", self.css)
        self.assertIn(".post-category-tag", self.css)
        self.assertIn("background-color: #C7CDE6", self.css)
        self.assertIn("color: #111942", self.css)
        self.assertIn("background-color: #111942 !important", self.css)
        self.assertIn("color: #C7CDE6 !important", self.css)

    def test_dashboard_state_interactions_are_client_side(self):
        self.assertEqual(len(re.findall(r"<a[^>]+data-nav-item", self.template)), 5)
        self.assertIn("const navItems = document.querySelectorAll('[data-nav-item]')", self.template)
        self.assertIn("const categoryTags = document.querySelectorAll('[data-category-tag]')", self.template)
        self.assertIn("function setActiveCategoryTag(activeTag)", self.template)
        self.assertIn("item.addEventListener('click'", self.template)
        self.assertIn("tag.addEventListener('click'", self.template)

    def test_dashboard_uses_relative_post_timestamp_value(self):
        self.assertIn("post.relative_created_at", self.template)
        self.assertNotIn("post.created_at[:10]", self.template)


class RelativeTimestampTest(unittest.TestCase):
    def test_relative_timestamps_match_social_timeline_copy(self):
        from app.routes.core import format_relative_time

        now = datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc)

        self.assertEqual(format_relative_time("2026-05-13T11:59:40Z", now), "Just now")
        self.assertEqual(format_relative_time("2026-05-13T11:55:00Z", now), "5 mins ago")
        self.assertEqual(format_relative_time("2026-05-13T10:00:00Z", now), "2 hrs ago")
        self.assertEqual(format_relative_time("2026-05-12T02:30:00Z", now), "Yesterday at 10:30 AM")
        self.assertEqual(format_relative_time("2026-05-10T16:00:00Z", now), "May 11")


if __name__ == "__main__":
    unittest.main()
