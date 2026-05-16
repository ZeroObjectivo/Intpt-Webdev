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

from app.routes.core import normalize_social_links_input


class ProfileSocialLinksValidationTest(unittest.TestCase):
    def test_accepts_supported_social_links_and_defaults_visibility(self):
        links = normalize_social_links_input([
            "facebook.com/example.user",
            "https://www.instagram.com/example.user/",
            "https://www.tiktok.com/@example.user/",
        ])
        self.assertEqual(
            links,
            [
                {"platform": "facebook", "url": "https://facebook.com/example.user", "visibility": "public", "position": 1},
                {"platform": "instagram", "url": "https://www.instagram.com/example.user", "visibility": "public", "position": 2},
                {"platform": "tiktok", "url": "https://www.tiktok.com/@example.user", "visibility": "public", "position": 3},
            ],
        )

    def test_accepts_linkedin_and_discord_links(self):
        links = normalize_social_links_input([
            "https://linkedin.com/in/example-user/",
            "discord.com/users/123456789",
        ], [
            "only_me",
            "public",
        ])
        self.assertEqual(
            links,
            [
                {"platform": "linkedin", "url": "https://linkedin.com/in/example-user", "visibility": "only_me", "position": 1},
                {"platform": "discord", "url": "https://discord.com/users/123456789", "visibility": "public", "position": 2},
            ],
        )

    def test_rejects_unsupported_domain(self):
        with self.assertRaisesRegex(ValueError, "Only supported social media links can be saved right now."):
            normalize_social_links_input(["https://youtube.com/@example"])

    def test_rejects_duplicate_links(self):
        with self.assertRaisesRegex(ValueError, "Duplicate social links are not allowed."):
            normalize_social_links_input([
                "https://facebook.com/example",
                "https://facebook.com/example/",
            ])

    def test_rejects_more_than_three_links(self):
        with self.assertRaisesRegex(ValueError, "You can save up to 3 social links only."):
            normalize_social_links_input([
                "https://facebook.com/one",
                "https://instagram.com/two",
                "https://facebook.com/three",
                "https://instagram.com/four",
            ])

    def test_empty_values_are_ignored_and_positions_are_compact(self):
        links = normalize_social_links_input([
            "https://facebook.com/example",
            "",
            "instagram.com/example.user",
        ], [
            "only_me",
            "public",
            "public",
        ])
        self.assertEqual(
            links,
            [
                {"platform": "facebook", "url": "https://facebook.com/example", "visibility": "only_me", "position": 1},
                {"platform": "instagram", "url": "https://instagram.com/example.user", "visibility": "public", "position": 2},
            ],
        )

    def test_rejects_invalid_visibility(self):
        with self.assertRaisesRegex(ValueError, "Please choose a valid visibility setting for each social link."):
            normalize_social_links_input([
                "https://facebook.com/example",
            ], [
                "friends_only",
            ])


if __name__ == "__main__":
    unittest.main()
