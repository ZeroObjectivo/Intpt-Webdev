from flask import Flask
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import os

def create_app():
    app = Flask(__name__)

    # Trust proxy headers (DO App Platform runs behind a reverse proxy)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

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
