import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIn0."
    "test-signature",
)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from postgrest.exceptions import APIError

from app import create_app


class FakeInsertQuery:
    def __init__(self, fake_supabase):
        self.fake_supabase = fake_supabase
        self.payload = None

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        self.fake_supabase.insert_payload = self.payload
        return type("Response", (), {"data": [self.payload]})()


class FakePostgrest:
    def __init__(self):
        self.auth_token = None

    def auth(self, token):
        self.auth_token = token


class FakeAuthSession:
    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token


class FakeAuthResponse:
    def __init__(self, access_token, refresh_token):
        self.session = FakeAuthSession(access_token, refresh_token)


class FakeAuth:
    def __init__(self):
        self.refresh_token = None

    def refresh_session(self, refresh_token):
        self.refresh_token = refresh_token
        return FakeAuthResponse("new-jwt-token", "new-refresh-token")


class FakeSupabase:
    def __init__(self):
        self.postgrest = FakePostgrest()
        self.auth = FakeAuth()
        self.insert_payload = None

    def table(self, table_name):
        if table_name != "posts":
            raise AssertionError(f"Unexpected table: {table_name}")
        return FakeInsertQuery(self)


class FakeSelectQuery:
    def __init__(self, fake_supabase, table_name):
        self.fake_supabase = fake_supabase
        self.table_name = table_name

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def single(self):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        self.fake_supabase.select_attempts += 1
        if self.fake_supabase.select_attempts == 1:
            raise APIError(
                {
                    "code": "PGRST303",
                    "message": "JWT expired",
                    "details": None,
                    "hint": None,
                }
            )

        if self.table_name == "profiles":
            return type(
                "Response",
                (),
                {
                    "data": {
                        "id": "user-123",
                        "full_name": "Test Heron",
                        "avatar_url": None,
                    }
                },
            )()

        return type(
            "Response",
            (),
            {
                "data": [
                    {
                        "profiles": {"full_name": "Test Heron", "avatar_url": None},
                        "category": "General",
                        "created_at": "2026-05-12T00:00:00Z",
                        "content": "Recovered after refresh",
                        "image_url": None,
                    }
                ]
            },
        )()


class FakeSupabaseWithExpiredJwt(FakeSupabase):
    def __init__(self):
        super().__init__()
        self.select_attempts = 0

    def table(self, table_name):
        return FakeSelectQuery(self, table_name)


class CreatePostTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()

    def test_create_post_applies_session_access_token_before_insert(self):
        fake_supabase = FakeSupabase()

        with self.client.session_transaction() as session:
            session["user"] = {"id": "user-123"}
            session["access_token"] = "jwt-token"

        with patch("app.routes.core.supabase", fake_supabase), patch(
            "app.routes.auth.supabase", fake_supabase
        ):
            response = self.client.post(
                "/posts/create",
                data={"content": "Hello Herons", "category": "General"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(fake_supabase.postgrest.auth_token, "jwt-token")
        self.assertEqual(
            fake_supabase.insert_payload,
            {
                "user_id": "user-123",
                "content": "Hello Herons",
                "category": "General",
            },
        )

    def test_dashboard_refreshes_expired_supabase_jwt_and_retries(self):
        fake_supabase = FakeSupabaseWithExpiredJwt()

        with self.client.session_transaction() as session:
            session["user"] = {
                "id": "user-123",
                "user_metadata": {"full_name": "Test Heron", "avatar_url": None},
            }
            session["access_token"] = "expired-jwt-token"
            session["refresh_token"] = "refresh-token"

        with patch("app.routes.core.supabase", fake_supabase), patch(
            "app.routes.auth.supabase", fake_supabase
        ):
            response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(fake_supabase.auth.refresh_token, "refresh-token")
        self.assertEqual(fake_supabase.postgrest.auth_token, "new-jwt-token")
        with self.client.session_transaction() as session:
            self.assertEqual(session["access_token"], "new-jwt-token")
            self.assertEqual(session["refresh_token"], "new-refresh-token")


if __name__ == "__main__":
    unittest.main()
