from services.supabase_client import engine
from sqlalchemy import text
with engine.connect() as conn:
    print("--- forbidden_words ---")
    res = conn.execute(text("SELECT * FROM public.forbidden_words"))
    for row in res:
        print(row)
    
    print("\n--- profiles schema check ---")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'profiles'"))
    print([r[0] for r in res])
