from services.supabase_client import engine
from sqlalchemy import text

def check_policies():
    sql = "SELECT tablename, policyname, cmd, qual FROM pg_policies WHERE schemaname = 'public'"
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        for row in result:
            print(f"Table: {row[0]} | Policy: {row[1]} | Command: {row[2]}")

if __name__ == "__main__":
    check_policies()
