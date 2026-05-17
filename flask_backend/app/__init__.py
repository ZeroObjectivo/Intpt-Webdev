import logging
import re
from markupsafe import Markup, escape
from flask import Flask, request, redirect, session, url_for
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timezone
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

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
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # CSRF protection for all POST forms
    csrf.init_app(app)

    @app.template_filter('datetime_obj')
    def datetime_obj(value):
        if not value:
            return None
        # Clean ISO string
        ts = value.replace('Z', '').split('.')[0]
        try:
            dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            # Fallback for full format
            dt = datetime.strptime(value.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
        
        # Ensure it's UTC aware
        return dt.replace(tzinfo=timezone.utc)

    @app.context_processor
    def inject_notifications():
        from flask import session
        from services.supabase_client import get_user_client
        from app.routes.core import build_notification_payload
        
        user = session.get('user')
        if not user:
            return {'notifications': [], 'unread_notifications_count': 0}
            
        try:
            client = get_user_client()
            payload = build_notification_payload(client, user['id'])
            
            return {
                'notifications': payload['items'],
                'unread_notifications_count': payload['unread_count']
            }
        except Exception as e:
            logger.error("Error injecting notifications: %s", e)
            return {'notifications': [], 'unread_notifications_count': 0}

    @app.context_processor
    def inject_now():
        return {'now': datetime.now(timezone.utc)}

    @app.context_processor
    def inject_timezone():
        from .routes.core import DISPLAY_TIMEZONE
        return {'DISPLAY_TIMEZONE': DISPLAY_TIMEZONE}

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

    _LINKIFY_RE = re.compile(r'(https?://[^\s<>"\']+)', re.IGNORECASE)

    @app.template_filter('linkify')
    def linkify_filter(text):
        """Escape text then convert URLs into clickable links."""
        safe_text = str(escape(text or ''))
        def _replace(m):
            url = m.group(1).rstrip('.,!?;:)')
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="text-blue-500 hover:underline break-all">{url}</a>'
        return Markup(_LINKIFY_RE.sub(_replace, safe_text))

    def normalize_domain(raw_value):
        raw = (raw_value or '').strip().lower()
        if not raw:
            return ''
        if '://' in raw:
            raw = raw.split('://', 1)[1]
        raw = raw.split('/', 1)[0]
        raw = raw.split('@')[-1]
        raw = raw.split(':', 1)[0]
        return raw.strip().strip('.')

    # Domain-based routing: separate admin (dev.) from public site
    admin_domain = normalize_domain(os.getenv('ADMIN_DOMAIN', ''))
    main_domain = normalize_domain(os.getenv('MAIN_DOMAIN', ''))

    def request_host_domain():
        forwarded = request.headers.get('X-Forwarded-Host', '')
        raw_host = forwarded.split(',')[0].strip() if forwarded else request.host
        return normalize_domain(raw_host)

    @app.before_request
    def enforce_domain_separation():
        host = request_host_domain()
        path = request.path
        user = session.get('user') or {}
        role = (user.get('role') or '').strip().lower()
        admin_portal_roles = {'admin', 'super_admin', 'superadmin', 'account_manager', 'content_moderator', 'content_manager'}
        is_admin_host = bool(admin_domain and host == admin_domain)
        if not is_admin_host and host.startswith('dev.'):
            is_admin_host = True

        # Allow static files on any domain
        if path.startswith('/static/'):
            return None

        # On the ADMIN domain (dev.heronshub.social)
        if is_admin_host:
            # Admin domain root should always land on its login screen.
            if path == '/':
                return redirect('/login')

            # Allow: login/auth/admin pages and notification sync APIs used by admin navbar
            allowed_prefixes = ('/login', '/auth/', '/admin/', '/sync/', '/notifications/')
            if path.startswith(allowed_prefixes):
                return None

            # Dev domain must never render user-facing pages.
            # Logged-in admin-portal roles are redirected to admin dashboard;
            # everyone else returns to login.
            if role in admin_portal_roles:
                return redirect(url_for('admin.dashboard'))
            return redirect('/login')

        # Non-admin hosts should not directly serve /admin/*
        if path.startswith('/admin/'):
            if admin_domain:
                scheme = request.headers.get('X-Forwarded-Proto', 'https')
                return redirect(f"{scheme}://{admin_domain}{path}")
            return redirect('/login')

        # On the MAIN domain (heronshub.social), prefer canonical admin redirect
        if main_domain and host in {main_domain, f"www.{main_domain}"}:
            if path.startswith('/admin/') and admin_domain:
                scheme = request.headers.get('X-Forwarded-Proto', 'https')
                return redirect(f"{scheme}://{admin_domain}{path}")

        return None

    return app
