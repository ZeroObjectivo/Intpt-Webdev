import datetime
import os
import sys
import unittest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIn0."
    "test-signature",
)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.routes.core import DISPLAY_TIMEZONE


class ProfileSettingsTemplateTest(unittest.TestCase):
    def test_profile_template_renders_posts_interactions_and_modal_copy(self):
        app = create_app()

        with app.test_request_context("/profile/u1"):
            template = app.jinja_env.get_template("profile_settings.html")
            html = template.render(
                user={
                    "id": "u1",
                    "full_name": "Juan C. Santos",
                    "email": "juan.santos@umak.edu.ph",
                    "avatar_url": None,
                    "course": "BS Computer Science",
                    "college": "CCIS",
                    "level": "3rd Year",
                    "bio": "CS student passionate about web development and AI.",
                    "contact_number": "09123456789",
                    "contact_privacy": "public",
                    "last_seen_label": "1 day ago",
                    "joined_label": "May 16, 2026",
                    "updated_at": "2026-05-16T00:00:00Z",
                },
                posts=[
                    {
                        "id": "p1",
                        "user_id": "u1",
                        "content": "Best resources for learning React and Next.js?",
                        "category": "Question",
                        "created_at": "2026-05-13T00:00:00Z",
                        "status": "approved",
                        "user_has_liked": False,
                        "likes_count": 87,
                        "comments_count": 23,
                        "relative_created_at": "3 days ago",
                        "embed": None,
                        "image_urls": [],
                        "image_url": None,
                        "profiles": {"full_name": "Juan C. Santos", "avatar_url": None, "college": "CCIS"},
                    }
                ],
                pending_posts=[
                    {
                        "id": "pp1",
                        "user_id": "u1",
                        "content": "This image post is waiting for approval.",
                        "category": "General",
                        "created_at": "2026-05-16T00:00:00Z",
                        "status": "pending",
                        "user_has_liked": False,
                        "likes_count": 0,
                        "comments_count": 0,
                        "relative_created_at": "1 hr ago",
                        "embed": None,
                        "image_urls": ["https://example.com/photo.jpg"],
                        "image_url": "https://example.com/photo.jpg",
                        "profiles": {"full_name": "Juan C. Santos", "avatar_url": None, "college": "CCIS"},
                    }
                ],
                interactions={
                    "stats": {"posts_count": 48, "likes_count": 1200, "comments_count": 234},
                    "likes": [
                        {
                            "created_at": "2026-05-15T00:00:00Z",
                            "post_id": "p10",
                            "post_content": "Shared a helpful guide for thesis work.",
                            "category": "General",
                            "relative_created_at": "1 day ago",
                        }
                    ],
                    "comments": [
                        {
                            "created_at": "2026-05-15T00:00:00Z",
                            "post_id": "p11",
                            "post_content": "How do you manage capstone timelines?",
                            "content": "Try breaking the milestones weekly.",
                            "category": "Question",
                            "relative_created_at": "1 day ago",
                        }
                    ],
                },
                college_options=[
                    {
                        "value": "CBFS",
                        "label": "CBFS",
                        "full_name": "College of Business and Financial Sciences",
                        "type": "College",
                        "group": "Colleges",
                    },
                    {
                        "value": "CCIS",
                        "label": "CCIS",
                        "full_name": "College of Computing and Information Sciences",
                        "type": "College",
                        "group": "Colleges",
                    },
                    {
                        "value": "IAD",
                        "label": "IAD",
                        "full_name": "Institute of Allied Health Sciences",
                        "type": "Institute",
                        "group": "Institutes",
                    },
                ],
                colleges=[
                    {"name": "CBFS", "full_name": "College of Business and Financial Sciences", "type": "College"},
                    {"name": "CCIS", "full_name": "College of Computing and Information Sciences", "type": "College"},
                ],
                institutes=[
                    {"name": "IAD", "full_name": "Institute of Allied Health Sciences", "type": "Institute"},
                ],
                social_links=[
                    {"platform": "facebook", "url": "https://facebook.com/juan", "label": "Facebook", "visibility": "public", "position": 1},
                    {"platform": "instagram", "url": "https://instagram.com/juan", "label": "Instagram", "visibility": "only_me", "position": 2},
                    {"platform": "linkedin", "url": "https://linkedin.com/in/juan", "label": "LinkedIn", "visibility": "public", "position": 3},
                ],
                public_social_links=[
                    {"platform": "facebook", "url": "https://facebook.com/juan", "label": "Facebook", "visibility": "public", "position": 1},
                    {"platform": "linkedin", "url": "https://linkedin.com/in/juan", "label": "LinkedIn", "visibility": "public", "position": 3},
                ],
                is_own_profile=True,
                now=datetime.datetime.now(datetime.timezone.utc),
                DISPLAY_TIMEZONE=DISPLAY_TIMEZONE,
                csrf_token=lambda: "token",
            )

        self.assertIn("Posts", html)
        self.assertIn("Interactions", html)
        self.assertIn("Pending Posts", html)
        self.assertIn("Posts awaiting approval", html)
        self.assertNotIn("Awaiting approval", html)
        self.assertIn("Edit Profile", html)
        self.assertNotIn("Last seen 1 day ago", html)
        self.assertIn("Joined May 16, 2026", html)
        self.assertIn('id="contactNumberFeedback"', html)
        self.assertIn('placeholder="09XXXXXXXXX"', html)
        self.assertIn("Select Unit", html)
        self.assertIn("Colleges", html)
        self.assertIn("Institutes", html)
        self.assertIn("Social Links", html)
        self.assertIn("Add up to 3 social links.", html)
        self.assertIn("Add social links", html)
        self.assertIn("Add another link", html)
        self.assertIn("Public", html)
        self.assertIn("Only me", html)
        self.assertIn('name="social_link_1"', html)
        self.assertIn('name="social_link_2"', html)
        self.assertIn('name="social_link_3"', html)
        self.assertIn('name="social_link_visibility_1"', html)
        self.assertIn("Facebook", html)
        self.assertIn("Instagram", html)
        self.assertIn("LinkedIn", html)
        self.assertIn("https://facebook.com/juan", html)
        self.assertIn("https://instagram.com/juan", html)
        self.assertIn("https://linkedin.com/in/juan", html)
        self.assertIn("CCIS - College of Computing and Information Sciences", html)
        self.assertIn("post-menu-dropdown absolute right-0 top-full mt-1 w-36 overflow-hidden rounded-lg", html)
        self.assertIn("backdrop-blur-xl", html)
        self.assertIn("hover:bg-slate-100/80", html)
        self.assertIn("hover:bg-red-50/85", html)
        self.assertIn("Recent liked posts", html)
        self.assertIn("Recent comments", html)


if __name__ == "__main__":
    unittest.main()
