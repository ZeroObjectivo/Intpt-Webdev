import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
from services.supabase_client import get_public_client


class FakeProfileQuery:
    def __init__(self, response_data):
        self.response_data = response_data

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def single(self):
        return self

    def execute(self):
        return SimpleNamespace(data=self.response_data)


class FakeProfileClient:
    def __init__(self, response_data):
        self.response_data = response_data

    def table(self, table_name):
        if table_name != "profiles":
            raise AssertionError(f"Unexpected table lookup: {table_name}")
        return FakeProfileQuery(self.response_data)


class AuthSessionRouteTest(unittest.TestCase):
    def test_supabase_clients_ignore_dead_proxy_environment(self):
        previous = {
            "HTTP_PROXY": os.environ.get("HTTP_PROXY"),
            "HTTPS_PROXY": os.environ.get("HTTPS_PROXY"),
            "ALL_PROXY": os.environ.get("ALL_PROXY"),
        }
        os.environ["HTTP_PROXY"] = "http://127.0.0.1:9"
        os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9"
        os.environ["ALL_PROXY"] = "http://127.0.0.1:9"
        try:
            client = get_public_client()
            self.assertFalse(client.auth._http_client.trust_env)
            self.assertFalse(client.postgrest.session.trust_env)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_access_token_flow_uses_neutral_profile_client_when_user_client_fails(self):
        fake_user = SimpleNamespace(
            id="user-123",
            email="student@umak.edu.ph",
            user_metadata={"full_name": "Test Student"},
        )
        fake_supabase = SimpleNamespace(
            auth=SimpleNamespace(
                get_user=lambda access_token: SimpleNamespace(user=fake_user),
                sign_out=lambda: None,
            )
        )
        neutral_profile_client = FakeProfileClient(
            {
                "id": "user-123",
                "role": "student",
                "full_name": "Test Student",
            }
        )

        with patch("app.routes.auth.supabase", fake_supabase), patch(
            "app.routes.auth.get_user_client",
            side_effect=AssertionError("token-bound profile client should not be used"),
        ), patch(
            "app.routes.auth.supabase_service",
            neutral_profile_client,
            create=True,
        ):
            response = self.client.get(
                "/auth/session?access_token=test-access-token",
                base_url="http://localhost:5000",
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auth/post-login")


if __name__ == "__main__":
    unittest.main()
