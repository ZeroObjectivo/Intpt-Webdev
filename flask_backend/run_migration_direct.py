import os
import logging
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_direct_sql():
    # Use the POOLER address instead of the DB address which is failing DNS
    project_id = os.environ.get("SUPABASE_PROJECT_ID", "")
    user = f"postgres.{project_id}" if project_id else os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    if not password:
        db_url = os.environ.get("DATABASE_URL", "")
        password = db_url.split(":")[2].split("@")[0] if db_url else ""
    host = os.environ.get("DB_HOST", "aws-0-ap-southeast-1.pooler.supabase.com")
    port = os.environ.get("DB_PORT", "5432")
    dbname = os.environ.get("DB_NAME", "postgres")

    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        sql_path = '../supabase/migrations/20260516000000_setup_colleges_institutes.sql'
        with open(sql_path, 'r') as f:
            sql = f.read()
            
        logger.info("Executing migration...")
        cur.execute(sql)
        logger.info("Migration successful!")
        
        cur.close()
        conn.close()
    except Exception as e:
        logger.error("Migration failed: %s", e)
        print("\nIF THIS FAILED: Please go to the Supabase SQL Editor and paste the content of:")
        print(os.path.abspath(sql_path))

if __name__ == "__main__":
    run_direct_sql()
