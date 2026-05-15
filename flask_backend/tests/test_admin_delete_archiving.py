import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


class AdminDeleteArchivingTest(unittest.TestCase):
    def test_archive_migration_exists(self):
        migration = read_text("../supabase/migrations/20260515000400_add_archived_posts_table.sql")
        self.assertIn("create table if not exists public.archived_posts", migration.lower())
        self.assertIn("purge_after", migration.lower())

    def test_admin_delete_route_archives_with_reason(self):
        admin_routes = read_text("app/routes/admin.py")
        self.assertIn("def get_delete_reason_payload()", admin_routes)
        self.assertIn("archive_post_snapshot(", admin_routes)
        self.assertIn("Post removed by moderation", admin_routes)

    def test_confirm_modal_supports_reason_dropdown(self):
        modal_template = read_text("app/templates/includes/modal.html")
        modal_js = read_text("app/static/js/modal.js")
        self.assertIn("confirmReasonContainer", modal_template)
        self.assertIn("confirmReasonSelect", modal_template)
        self.assertIn("options.reasons", modal_js)
        self.assertIn("options.requireReason", modal_js)

    def test_admin_content_delete_passes_reason_payload(self):
        content_manage = read_text("app/templates/admin/content_manage.html")
        self.assertIn("reasonOptions", content_manage)
        self.assertIn("reason: payload.reason", content_manage)
        self.assertIn("note: payload.note", content_manage)

    def test_core_interaction_notifications_added(self):
        core_routes = read_text("app/routes/core.py")
        self.assertIn("def push_notification(", core_routes)
        self.assertIn("New like on your post", core_routes)
        self.assertIn("New comment on your post", core_routes)
        self.assertIn("New reply to your comment", core_routes)


if __name__ == "__main__":
    unittest.main()
