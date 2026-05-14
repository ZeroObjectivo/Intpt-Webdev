from flask import Flask
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timezone
from werkzeug.middleware.proxy_fix import ProxyFix
import os

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)

    # Trust proxy headers (DO App Platform runs behind a reverse proxy)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Configuration — SECRET_KEY must be set via environment variable
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is not set.")
    app.config['SECRET_KEY'] = secret_key

    # CSRF protection for all POST forms
    csrf.init_app(app)

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
        from services.supabase_client import get_user_client
        
        user = session.get('user')
        if not user:
            return {'notifications': [], 'unread_notifications_count': 0}
            
        try:
            # Use the current user's token-backed client so this works even without service key.
            client = get_user_client()
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
        return {'now': datetime.now(timezone.utc)}

    # Register Blueprints
    from .routes.core import core
    from .routes.auth import auth
    from .routes.admin import admin

    app.register_blueprint(core)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    return app
