from services.supabase_client import engine
from sqlalchemy import text
import os

def run_migration(filename):
    migration_path = os.path.join('..', 'supabase', 'migrations', filename)
    with engine.connect() as conn:
        with open(migration_path, 'r') as f:
            sql = f.read()
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"Migration {filename} applied successfully!")
            except Exception as e:
                print(f"Error applying migration {filename}: {e}")

if __name__ == "__main__":
    run_migration('20260513000700_allow_dispute_insert.sql')
