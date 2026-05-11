import os
from dotenv import load_dotenv
from sqlalchemy import text
from services.supabase_client import supabase, engine

# Load environment variables
load_dotenv()

def test_connections():
    print("--- TESTING SUPABASE CONNECTIONS ---")
    
    # 1. Test Supabase Client (API)
    print("\n1. Testing Supabase API Client...")
    try:
        # Just try to fetch some metadata or a simple health check
        # Since we don't have tables yet, we'll just check if the client exists
        if supabase:
            print("✔ Supabase API Client: SUCCESS")
        else:
            print("✘ Supabase API Client: FAILED")
    except Exception as e:
        print(f"✘ Supabase API Client: ERROR - {e}")

    # 2. Test PostgreSQL Connection (SQLAlchemy)
    print("\n2. Testing PostgreSQL Connection (Direct)...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()
            print(f"✔ PostgreSQL Connection: SUCCESS")
            print(f"   Database Version: {version[0]}")
    except Exception as e:
        print(f"✘ PostgreSQL Connection: FAILED")
        print(f"   Error: {e}")
        print("\nTIP: Make sure your DATABASE_URL is correct and your IP is allowed in Supabase (Project Settings > Database > Network Restrictions).")

if __name__ == "__main__":
    test_connections()
