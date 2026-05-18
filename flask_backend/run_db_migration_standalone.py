import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def run_migration():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        sql = """
        ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS hosting_college text;
        COMMENT ON COLUMN public.posts.hosting_college IS 'The specific college or institute hosting an event.';
        """
        cur.execute(sql)
        conn.commit()
        print("Migration applied successfully.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    run_migration()
