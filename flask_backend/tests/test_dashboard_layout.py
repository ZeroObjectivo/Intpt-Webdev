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
        self.core_route = (PROJECT_ROOT / "app" / "routes" / "core.py").read_text()
        self.sidebar_include = (PROJECT_ROOT / "app" / "templates" / "includes" / "primary_sidebar.html").read_text()

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
        self.assertNotIn("Settings", self.sidebar_include)

    def test_primary_nav_links_use_current_dashboard_navigation_structure(self):
        nav_rule = re.search(r"\.primary-nav-link\s*\{(?P<body>.*?)\}", self.css, re.S)
        active_rule = re.search(r"\.primary-nav-link\.active\s*\{(?P<body>.*?)\}", self.css, re.S)

        self.assertIsNotNone(nav_rule)
        self.assertIsNotNone(active_rule)
        self.assertIn("width: 100%", nav_rule.group("body"))
        self.assertIn("border-radius: var(--hh-radius)", nav_rule.group("body"))
        self.assertIn("border-radius: var(--hh-radius)", self.css)
        self.assertIn("background: var(--hh-blue-500)", active_rule.group("body"))
        self.assertIn("{% include 'includes/primary_sidebar.html' %}", self.template)
        self.assertIn("Home Feed", self.sidebar_include)
        self.assertIn("Marketplace", self.sidebar_include)
        self.assertIn("Event Calendar", self.sidebar_include)
        self.assertIn("Scholarship", self.sidebar_include)
        self.assertIn("UMak COOP", self.sidebar_include)
        self.assertIn("About", self.sidebar_include)
        self.assertNotIn("Settings", self.sidebar_include)
        support_index = self.sidebar_include.index("<span>Heron Support</span>")
        about_index = self.sidebar_include.index("<span>About</span>")
        self.assertLess(support_index, about_index)

    def test_dashboard_sidebar_keeps_about_as_last_nav_item_and_restyles_primary_actions(self):
        self.assertIn(".primary-sidebar-shell", self.css)
        sidebar_shell_rule = re.search(r"\.primary-sidebar-shell\s*\{(?P<body>.*?)\}", self.css, re.S)
        self.assertIsNotNone(sidebar_shell_rule)
        sidebar_shell_body = sidebar_shell_rule.group("body")
        self.assertIn("background: transparent", sidebar_shell_body)
        self.assertNotIn(".primary-nav-footer", self.css)
        self.assertNotIn("margin-top: auto", self.css)
        self.assertNotIn("border: 1px solid var(--hh-border)", sidebar_shell_body)
        self.assertIn("border: 1px solid currentColor", self.css)
        self.assertIn("font-weight: 700", self.css)
        self.assertIn("border-current", self.template)
        self.assertIn("font-bold", self.template)

    def test_secondary_views_share_primary_sidebar_include(self):
        event_template = (PROJECT_ROOT / "app" / "templates" / "event_calendar.html").read_text()
        scholarship_template = (PROJECT_ROOT / "app" / "templates" / "scholarship.html").read_text()
        coop_template = (PROJECT_ROOT / "app" / "templates" / "umak_coop.html").read_text()

        for template in (event_template, scholarship_template, coop_template):
            self.assertIn("{% include 'includes/primary_sidebar.html' %}", template)
            self.assertNotIn(">UMak Coop<", template)
            self.assertNotIn('class="primary-nav-link rounded-lg"', template)

    def test_secondary_views_do_not_render_deprecated_settings_nav_item(self):
        event_template = (PROJECT_ROOT / "app" / "templates" / "event_calendar.html").read_text()
        scholarship_template = (PROJECT_ROOT / "app" / "templates" / "scholarship.html").read_text()
        coop_template = (PROJECT_ROOT / "app" / "templates" / "umak_coop.html").read_text()

        self.assertNotIn("<span>Settings</span>", self.sidebar_include)
        for template in (event_template, scholarship_template, coop_template, self.template):
            self.assertNotIn(">Settings<", template)

    def test_dashboard_category_tags_use_standard_dark_palette(self):
        post_tag_matches = re.findall(
            r"<span class=\"(?P<classes>[^\"]*post-category-tag[^\"]*)\"",
            self.template,
        )
        filter_pill_matches = re.findall(r"class=\"pill [^\"]+\"", self.template)

        self.assertGreaterEqual(len(filter_pill_matches), 6)
        self.assertIn("badge-all", self.template)
        self.assertIn("badge-general", self.template)
        self.assertIn("badge-lost-found", self.template)
        self.assertIn("badge-heron-business", self.template)
        self.assertIn("badge-question", self.template)
        self.assertIn("badge-events", self.template)

        self.assertIn(".badge-all", self.css)
        self.assertIn(".badge-general", self.css)
        self.assertIn(".badge-lost-found", self.css)
        self.assertIn(".badge-heron-business", self.css)
        self.assertIn(".badge-question", self.css)
        self.assertIn(".badge-events", self.css)
        self.assertIn(".pill.active", self.css)
        self.assertNotIn("#fef08a", self.css)

    def test_dashboard_state_interactions_are_client_side(self):
        self.assertGreaterEqual(len(re.findall(r"(?:<a|<button)[^>]+data-nav-item", self.template)), 7)
        self.assertIn('id="mobileCategoryFilter"', self.template)
        self.assertIn("window.dashboardSyncConfig", self.template)
        self.assertIn("js/realtime_sync.js", self.template)

    def test_dashboard_filter_header_uses_icon_without_helper_copy(self):
        self.assertNotIn("Use a category tag to focus what appears in your timeline.", self.template)
        self.assertNotIn(">Filter:<", self.template)
        self.assertIn('class="feed-filter-title-icon"', self.template)
        self.assertIn('class="sr-only">Filter posts</span>', self.template)

    def test_trending_now_uses_card_layout_with_rank_and_status(self):
        self.assertIn('class="trending-rank"', self.template)
        self.assertIn('class="trending-pill-row"', self.template)
        self.assertIn('class="badge badge-events trending-pill"', self.template)
        self.assertIn('class="trending-description line-clamp-2"', self.template)
        self.assertIn('class="trending-likes"', self.template)
        self.assertIn('class="trending-chevron"', self.template)
        self.assertIn(".trending-pill", self.css)
        self.assertIn(".trending-description", self.css)
        self.assertIn(".trending-likes", self.css)

    def test_upcoming_events_places_status_under_details_without_label(self):
        self.assertIn('<p>{{ event.time_display }}</p>', self.template)
        self.assertIn('class="event-location"', self.template)
        self.assertNotIn('class="event-status-stack"', self.template)
        self.assertNotIn(">status<", self.template)
        self.assertIn(".event-location", self.css)

    def test_create_post_modal_has_dynamic_category_fields(self):
        self.assertIn('id="createPostForm"', self.template)
        self.assertIn('enctype="multipart/form-data"', self.template)
        self.assertIn('id="createPostCategory"', self.template)
        self.assertIn('id="lostFoundFields" class="category-specific-fields hidden"', self.template)
        self.assertIn('id="businessFields" class="category-specific-fields hidden', self.template)
        self.assertIn('id="eventFields" class="category-specific-fields hidden', self.template)
        self.assertIn('<input type="hidden" name="status" value="Lost" disabled>', self.template)
        self.assertNotIn('value="Found"', self.template)
        self.assertNotIn('role="radiogroup"', self.template)
        self.assertIn('name="product_name"', self.template)
        self.assertIn('name="price" type="number"', self.template)
        self.assertIn('name="event_title"', self.template)
        self.assertIn('name="event_date" type="datetime-local"', self.template)
        self.assertIn('name="location" type="text"', self.template)
        self.assertIn('name="hosting_college"', self.template)
        self.assertIn("function initCategoryToggle()", self.template)
        self.assertIn("categorySelect.addEventListener('change'", self.template)
        self.assertIn("function hideCategoryFields()", self.template)
        self.assertIn("function showActiveCategoryFields()", self.template)
        self.assertNotIn("function setLostFoundStatus(activeOption)", self.template)
        self.assertNotIn(".lost-found-status-option", self.css)

    def test_inactive_category_fields_do_not_leak_status_values(self):
        self.assertIn('<input type="hidden" name="status" value="Lost" disabled>', self.template)
        self.assertIn("group.querySelectorAll('input, select, textarea').forEach((field) => {", self.template)
        self.assertIn("field.disabled = true;", self.template)
        self.assertIn("field.disabled = false;", self.template)

    def test_create_post_category_sections_match_modal_surface_style(self):
        shared_surface = "category-specific-fields hidden space-y-3 bg-white rounded-[12px] border border-slate-200 shadow-sm overflow-hidden p-3 animate-in fade-in zoom-in duration-200 font-sans"

        self.assertIn(f'id="businessFields" class="{shared_surface}"', self.template)
        self.assertIn(f'id="eventFields" class="{shared_surface}"', self.template)
        self.assertIn('class="grid grid-cols-1 sm:grid-cols-2 gap-3"', self.template)
        self.assertIn('id="businessProductName" name="product_name" type="text" class="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-[14px] font-sans', self.template)
        self.assertIn('id="hostingCollege" name="hosting_college" class="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-[14px] font-sans', self.template)

    def test_heron_business_filter_uses_stored_category_value(self):
        self.assertIn("url_for('core.dashboard', category='Heron Business')", self.template)
        self.assertIn("active_category == 'Heron Business'", self.template)
        self.assertIn('<option value="Heron Business">Heron Business</option>', self.template)
        self.assertNotIn("url_for('core.dashboard', category='Buy & Sell')", self.template)
        self.assertIn("HERON_BUSINESS_CATEGORIES = ['Heron Business', 'Buy & Sell']", self.core_route)
        self.assertIn("category = normalize_dashboard_category(request.args.get('category'))", self.core_route)
        self.assertIn("query = query.in_('category', HERON_BUSINESS_CATEGORIES)", self.core_route)

    def test_create_post_modal_has_image_upload_and_mock_submission_js(self):
        self.assertRegex(
            self.template,
            r'id="globalImageUpload" name="image" accept="image/\*"[^>]*class="hidden"'
        )
        self.assertIn('id="addImageTrigger"', self.template)
        self.assertIn('id="globalImageFilename"', self.template)
        self.assertIn('id="imagePreviewContainer"', self.template)
        self.assertIn("let selectedFiles = []", self.template)
        self.assertIn("function renderPreviews()", self.template)
        self.assertIn("globalImageUpload.onchange = () => {", self.template)
        self.assertIn("new DataTransfer()", self.template)
        self.assertIn("card.addEventListener('dragstart'", self.template)
        self.assertIn("function initFormValidation()", self.template)
        self.assertIn("function validateActiveCategory()", self.template)
        self.assertIn("case 'Lost & Found':", self.template)
        self.assertIn("case 'Heron Business':", self.template)
        self.assertIn("case 'Events':", self.template)
        self.assertIn("Maximum 5 images allowed.", self.template)
        self.assertIn("imageLimitCounter", self.template)
        self.assertIn(".fb-grid", self.css)

    def test_event_hosting_college_options_are_exact(self):
        expected_options = [
            "CLAS - College of Liberal Arts and Sciences",
            "CHK - College of Human Kinetics",
            "CBFS - College of Business and Financial Sciences",
            "CCIS - College of Computing and Information Sciences",
            "CITE - College of Innovative Teacher Education",
            "CITE-HSU - Higher School ng UMak",
            "CGPP - College of Governance and Public Policy",
            "CCSE - College of Construction Sciences and Engineering",
            "CET - College of Engineering Technology",
            "CTHM - College of Tourism and Hospitality Management",
            "CCAPS - College of Continuing, Advanced and Professional Studies",
        ]

        for option in expected_options:
            self.assertIn(f'<option value="{option}">{option}</option>', self.template)

    def test_dashboard_feed_removes_static_structured_mockups(self):
        self.assertNotIn("Structured Post Examples", self.template)
        self.assertNotIn("mock-post-examples", self.template)
        self.assertNotIn("mock-post-card", self.template)
        self.assertNotIn("mock-post-image", self.template)
        self.assertNotIn(".mock-post-examples", self.css)
        self.assertNotIn(".mock-post-card", self.css)
        self.assertNotIn(".business-product-summary", self.css)
        self.assertNotIn(".event-detail-card", self.css)

    def test_dashboard_right_sidebar_is_sticky(self):
        self.assertIn('class="dashboard-container min-h-screen"', self.template)
        self.assertIn('class="sidebar sticky top-20 h-full"', self.template)

        container_rule = re.search(r"\.dashboard-container\s*\{(?P<body>.*?)\}", self.css, re.S)
        self.assertIsNotNone(container_rule)
        self.assertIn("grid-template-columns: minmax(190px, 220px) minmax(0, 1fr) minmax(280px, 320px)", container_rule.group("body"))

        sidebar_rule = re.search(r"\.sidebar\s*\{(?P<body>.*?)\}", self.css, re.S)
        self.assertIsNotNone(sidebar_rule)
        self.assertIn("position: sticky", sidebar_rule.group("body"))
        self.assertIn("top: 112px", sidebar_rule.group("body"))
        self.assertIn("max-height: calc(100vh - 112px)", sidebar_rule.group("body"))

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
        self.assertEqual(format_relative_time("2026-05-10T16:00:00Z", now), "May 11, 2026 at 12:00 AM")


if __name__ == "__main__":
    unittest.main()
