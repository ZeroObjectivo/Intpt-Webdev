import os
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env
load_dotenv()

# Supabase Credentials
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
db_url: str = os.getenv("DATABASE_URL")

print("SUPABASE_URL:", url)
print("SUPABASE_KEY:", key)

# 1. Supabase Client (For Auth, Storage, Edge Functions)
supabase: Client = create_client(url, key)

# 2. Supabase Service Client (Bypasses RLS - Admin Use Only)
# This client should NEVER be used for general user operations
supabase_service: Client = None
if service_key:
    supabase_service = create_client(url, service_key)

# 3. SQLAlchemy Engine (For direct PostgreSQL operations)
# We use SQLAlchemy for robust database management
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Helper function to get a database session.
    Ensures the session is closed after use.
    """
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def init_supabase():
    """
    Verifies that the credentials are loaded properly.
    """
    if not url or not key or "your-project-id" in url:
        print("Error: Supabase credentials not found. Please update your .env file.")
        return False
    return True
