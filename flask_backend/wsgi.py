import os
from dotenv import load_dotenv
from app import create_app
from services.supabase_client import init_supabase

# Load environment variables
load_dotenv()

# Initialize Flask app — gunicorn imports this as `wsgi:app`
app = create_app()

# Simple route to check status
@app.route('/db-status')
def db_status():
    if init_supabase():
        return {"status": "success", "message": "Supabase configuration loaded!"}
    else:
        return {"status": "error", "message": "Supabase configuration missing!"}, 500

if __name__ == '__main__':
    # Initialize connection check
    print("Checking Supabase Connection...")
    if init_supabase():
        print("✔ Supabase Client Initialized")
    else:
        print("✘ Supabase Client Failed to Initialize. Check your .env file.")

    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
