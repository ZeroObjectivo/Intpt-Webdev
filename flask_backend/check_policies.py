from services.supabase_client import engine
from sqlalchemy import text

def check_policies():
    sql = """
    SELECT schemaname, tablename, policyname, cmd, qual, with_check 
    FROM pg_policies 
    WHERE schemaname IN ('public', 'storage')
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        print(f"{'Schema':<10} | {'Table':<15} | {'Command':<10} | {'Policy Name'}")
        print("-" * 60)
        for row in result:
            print(f"Schema: {row[0]} | Table: {row[1]} | Command: {row[2]} | Name: {row[3]}")
            print(f"  Qual: {row[4]}")
            print(f"  Check: {row[5]}")
            print("-" * 20)

if __name__ == "__main__":
    check_policies()
