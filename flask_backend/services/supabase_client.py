import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
from gotrue.http_clients import SyncClient as GoTrueHttpClient
from postgrest import SyncPostgrestClient
from postgrest.constants import DEFAULT_POSTGREST_CLIENT_TIMEOUT
from postgrest.utils import SyncClient as PostgrestHttpClient
from storage3 import SyncStorageClient
from storage3.constants import DEFAULT_TIMEOUT as DEFAULT_STORAGE_CLIENT_TIMEOUT
from storage3.utils import SyncClient as StorageHttpClient
from supabase import Client
from supabase._sync.auth_client import SyncSupabaseAuthClient
from supabase._sync.client import SyncClient as SupabaseSyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import session as flask_session

# Load environment variables from .env
load_dotenv()

# Supabase Credentials (strip whitespace/newlines from env vars)
url: str = os.getenv("SUPABASE_URL", "").strip()
key: str = (
    os.getenv("SUPABASE_KEY", "")
    or os.getenv("SUPABASE_ANON_KEY", "")
).strip()
service_key: str = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.getenv("SUPABASE_SERVICE_KEY", "")
    or os.getenv("SUPABASE_SECRET_KEY", "")
).strip() or None
db_url: str = os.getenv("DATABASE_URL", "").strip()


class NoProxySupabaseClient(SupabaseSyncClient):
    """Supabase client that ignores inherited proxy environment variables."""

    @staticmethod
    def _init_supabase_auth_client(
        auth_url: str,
        client_options,
    ) -> SyncSupabaseAuthClient:
        return SyncSupabaseAuthClient(
            url=auth_url,
            auto_refresh_token=client_options.auto_refresh_token,
            persist_session=client_options.persist_session,
            storage=client_options.storage,
            headers=client_options.headers,
            flow_type=client_options.flow_type,
            http_client=GoTrueHttpClient(
                verify=True,
                follow_redirects=True,
                http2=True,
                trust_env=False,
            ),
        )

    @staticmethod
    def _init_postgrest_client(
        rest_url: str,
        headers: dict,
        schema: str,
        timeout=DEFAULT_POSTGREST_CLIENT_TIMEOUT,
    ) -> SyncPostgrestClient:
        postgrest = SyncPostgrestClient(
            rest_url,
            headers=headers,
            schema=schema,
            timeout=timeout,
        )
        postgrest.session = PostgrestHttpClient(
            base_url=rest_url,
            headers=headers,
            timeout=timeout,
            verify=True,
            follow_redirects=True,
            http2=True,
            trust_env=False,
        )
        return postgrest

    @staticmethod
    def _init_storage_client(
        storage_url: str,
        headers: dict,
        storage_client_timeout: int = DEFAULT_STORAGE_CLIENT_TIMEOUT,
    ) -> SyncStorageClient:
        storage = SyncStorageClient(storage_url, headers, storage_client_timeout)
        storage.session = StorageHttpClient(
            base_url=storage_url,
            headers=headers,
            timeout=storage_client_timeout,
            verify=True,
            follow_redirects=True,
            http2=True,
            trust_env=False,
        )
        return storage


def create_no_proxy_client(supabase_url: str, supabase_key: str) -> Client:
    return NoProxySupabaseClient.create(supabase_url, supabase_key)

# Shared client for auth operations (sign_in, sign_out, get_user, exchange_code)
# These don't use per-user tokens on the postgrest layer.
supabase: Client = create_no_proxy_client(url, key)

# Service client (bypasses RLS — admin use only)
supabase_service: Client = None
if service_key:
    supabase_service = create_no_proxy_client(url, service_key)


def get_public_client() -> Client:
    """
    Create a fresh anonymous Supabase client for reads that do not depend on
    the current user's JWT. This is useful during auth bootstrap before the
    app can safely rely on a newly issued access token for PostgREST.
    """
    return create_no_proxy_client(url, key)


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
        return create_no_proxy_client(url, key)

    client = create_no_proxy_client(url, key)
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
        logger.error("Supabase credentials not found. Please update your .env file.")
        return False
    return True
