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
    migrations = [
        '20260513000700_allow_dispute_insert.sql',
        '20260514000000_admin_role_management_policies.sql',
        '20260514000300_add_flag_status.sql',
        '20260514000400_add_event_title.sql',
        '20260514000500_fix_warnings_policies.sql',
        '20260514000600_sync_notifications_schema.sql',
        '20260515000400_add_archived_posts_table.sql'
    ]
    for m in migrations:
        run_migration(m)
