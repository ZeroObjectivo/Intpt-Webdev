from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-for-university-social-platform')
    
    # Register Blueprints
    from .routes.core import core
    from .routes.auth import auth
    
    app.register_blueprint(core)
    app.register_blueprint(auth)
    
    return app
