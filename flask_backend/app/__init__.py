from flask import Flask, request, redirect, session
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

    @app.context_processor
    def inject_supabase_keys():
        return {
            'SUPABASE_URL': os.getenv('SUPABASE_URL'),
            'SUPABASE_ANON_KEY': os.getenv('SUPABASE_KEY')
        }

    # Register Blueprints
    from .routes.core import core
    from .routes.auth import auth
    from .routes.admin import admin

    app.register_blueprint(core)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    # Domain-based routing: separate admin (dev.) from public site
    admin_domain = os.getenv('ADMIN_DOMAIN', '').strip()
    main_domain = os.getenv('MAIN_DOMAIN', '').strip()

    if admin_domain:
        @app.before_request
        def enforce_domain_separation():
            host = request.host.split(':')[0]  # strip port for local dev
            path = request.path

            # Allow static files on any domain
            if path.startswith('/static/'):
                return None

            # On the ADMIN domain (dev.heronshub.social)
            if host == admin_domain:
                # Allow: login page, auth routes (login flow + callback)
                allowed_prefixes = ('/login', '/auth/', '/admin/')
                if path == '/' or path.startswith(allowed_prefixes):
                    return None

                # Logged-in non-admin trying to reach other pages → reject
                user = session.get('user')
                if user and user.get('role') not in ('admin', 'super_admin', 'superadmin'):
                    scheme = request.headers.get('X-Forwarded-Proto', 'https')
                    return redirect(f"{scheme}://{main_domain}/dashboard")

                # Any other path on dev domain → send to main domain
                if main_domain and not path.startswith(allowed_prefixes):
                    scheme = request.headers.get('X-Forwarded-Proto', 'https')
                    return redirect(f"{scheme}://{main_domain}{path}")

                return None

            # On the MAIN domain (heronshub.social)
            if host == main_domain or (main_domain and host == main_domain):
                # Redirect /admin/* to the admin domain
                if path.startswith('/admin/'):
                    scheme = request.headers.get('X-Forwarded-Proto', 'https')
                    return redirect(f"{scheme}://{admin_domain}{path}")

            return None

    return app
