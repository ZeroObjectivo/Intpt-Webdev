import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


class SecurityHardeningTest(unittest.TestCase):
    def test_app_initializes_csrf_protection(self):
        app_init = read_text("app/__init__.py")
        self.assertIn("from flask_wtf.csrf import CSRFProtect", app_init)
        self.assertIn("csrf = CSRFProtect()", app_init)
        self.assertIn("csrf.init_app(app)", app_init)

    def test_requirements_include_flask_wtf(self):
        requirements = read_text("requirements.txt")
        self.assertIn("Flask-WTF==", requirements)

    def test_base_templates_expose_csrf_meta(self):
        base_html = read_text("app/templates/base.html")
        admin_base_html = read_text("app/templates/admin/admin_base.html")
        self.assertIn('meta name="csrf-token"', base_html)
        self.assertIn('meta name="csrf-token"', admin_base_html)

    def test_post_forms_include_csrf_hidden_input(self):
        dashboard = read_text("app/templates/dashboard.html")
        onboarding = read_text("app/templates/onboarding.html")
        profile_settings = read_text("app/templates/profile_settings.html")
        admin_forbidden = read_text("app/templates/admin/forbidden_words.html")
        admin_user_manage = read_text("app/templates/admin/user_manage.html")

        self.assertGreaterEqual(dashboard.count('name="csrf_token"'), 2)
        self.assertIn('name="csrf_token"', onboarding)
        self.assertGreaterEqual(profile_settings.count('name="csrf_token"'), 3)
        self.assertGreaterEqual(admin_forbidden.count('name="csrf_token"'), 2)
        self.assertIn('name="csrf_token"', admin_user_manage)

    def test_js_post_fetch_calls_send_csrf_header(self):
        modal_js = read_text("app/static/js/modal.js")
        dashboard = read_text("app/templates/dashboard.html")
        profile_settings = read_text("app/templates/profile_settings.html")
        admin_content = read_text("app/templates/admin/content_manage.html")

        self.assertIn("function getCSRFToken()", modal_js)
        self.assertIn("/comments/${commentId}/update", modal_js)
        self.assertIn("/comments/${commentId}/delete", modal_js)
        self.assertIn("/posts/${currentPost.id}/comments", modal_js)
        self.assertIn("/posts/${postId}/like", modal_js)
        self.assertIn("'X-CSRFToken': getCSRFToken()", modal_js)

        self.assertIn("'X-CSRFToken': getCSRFToken()", dashboard)
        self.assertIn("'X-CSRFToken': getCSRFToken()", profile_settings)

        self.assertIn("/admin/warn-user", admin_content)
        self.assertIn("/admin/posts/${postId}/flag", admin_content)
        self.assertIn("/admin/comments/${commentId}/flag", admin_content)
        self.assertIn("'X-CSRFToken': getCSRFToken()", admin_content)

    def test_routes_use_per_request_client_helper(self):
        client_helper = read_text("services/supabase_client.py")
        core_routes = read_text("app/routes/core.py")
        admin_routes = read_text("app/routes/admin.py")

        self.assertIn("def get_user_client", client_helper)
        self.assertIn("get_user_client(", core_routes)
        self.assertIn("get_user_client(", admin_routes)


if __name__ == "__main__":
    unittest.main()
