from flask import Flask
from datetime import datetime
import os

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-for-university-social-platform')

    # Custom Jinja filters
    @app.template_filter('datetime_obj')
    def datetime_obj(value):
        # Clean ISO string
        ts = value.replace('Z', '').split('.')[0]
        try:
            return datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            # Fallback for full format
            return datetime.strptime(value.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')

    @app.context_processor
    def inject_notifications():
        from flask import session
        from services.supabase_client import supabase, supabase_service
        
        user = session.get('user')
        if not user:
            return {'notifications': [], 'unread_notifications_count': 0}
            
        try:
            # Use service client to bypass RLS for fetching notifications in context processor
            client = supabase_service if supabase_service else supabase
            res = client.table('notifications')\
                .select("*")\
                .eq('user_id', user['id'])\
                .order('created_at', desc=True)\
                .limit(5).execute()
            
            notifications = res.data
            unread_count = len([n for n in notifications if not n.get('is_read')])
            
            return {
                'notifications': notifications,
                'unread_notifications_count': unread_count
            }
        except Exception as e:
            print(f"Error injecting notifications: {e}")
            return {'notifications': [], 'unread_notifications_count': 0}

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    # Register Blueprints
    from .routes.core import core
    from .routes.auth import auth
    from .routes.admin import admin

    app.register_blueprint(core)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    return app
