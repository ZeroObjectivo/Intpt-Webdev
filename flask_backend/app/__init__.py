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
    def inject_now():
        return {'now': datetime.utcnow()}

    # Register Blueprints
    from .routes.core import core
    from .routes.auth import auth

    app.register_blueprint(core)
    app.register_blueprint(auth)

    return app
