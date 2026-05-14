from services.supabase_client import engine
from sqlalchemy import text
import os

with engine.connect() as conn:
    migration_path = os.path.join('..', 'supabase', 'migrations', '20260514000700_fix_notifications_policy.sql')
    with open(migration_path, 'r') as f:
        sql = f.read()
        # Split by semicolon but handle potential issues with triggers/functions if they were there
        # For this simple migration, executing the whole block is fine
        try:
            conn.execute(text(sql))
            conn.commit()
            print("Migration applied successfully!")
        except Exception as e:
            print(f"Error applying migration: {e}")
