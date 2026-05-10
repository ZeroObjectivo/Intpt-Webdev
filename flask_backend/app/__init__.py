from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'dev-key-for-university-social-platform'
    
    # Register Blueprints
    from .routes import core
    app.register_blueprint(core)
    
    return app
