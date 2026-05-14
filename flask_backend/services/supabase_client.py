import os
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import session as flask_session

# Load environment variables from .env
load_dotenv()

# Supabase Credentials (strip whitespace/newlines from env vars)
url: str = os.getenv("SUPABASE_URL", "").strip()
key: str = os.getenv("SUPABASE_KEY", "").strip()
service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None
db_url: str = os.getenv("DATABASE_URL", "").strip()

# Shared client for auth operations (sign_in, sign_out, get_user, exchange_code)
# These don't use per-user tokens on the postgrest layer.
supabase: Client = create_client(url, key)

# Service client (bypasses RLS — admin use only)
supabase_service: Client = None
if service_key:
    supabase_service = create_client(url, service_key)


def get_user_client() -> Client:
    """
    Create a fresh Supabase client authenticated with the current user's
    access token. This avoids the global client's token being shared
    across concurrent requests.

    Use this for all DB/storage operations that depend on the user's identity.
    Falls back to an anonymous client if no access_token in session.
    """
    access_token = flask_session.get('access_token')
    if not access_token:
        return create_client(url, key)

    client = create_client(url, key)
    client.postgrest.auth(access_token)

    # Set storage auth header
    if hasattr(client, 'storage'):
        if hasattr(client.storage, '_client') and hasattr(client.storage._client, 'headers'):
            client.storage._client.headers.update({"Authorization": f"Bearer {access_token}"})

    return client


# SQLAlchemy Engine (for direct PostgreSQL operations)
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Helper function to get a database session.
    Caller is responsible for closing the session.
    """
    return SessionLocal()


def init_supabase():
    """
    Verifies that the credentials are loaded properly.
    """
    if not url or not key or "your-project-id" in url:
        print("Error: Supabase credentials not found. Please update your .env file.")
        return False
    return True
