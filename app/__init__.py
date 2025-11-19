"""
Flask application factory
"""
from flask import Flask
from config import Config

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Load user settings on startup
    config_class.load_user_settings()

    # Register blueprints
    from app.routes import api, settings
    app.register_blueprint(api.bp)
    app.register_blueprint(settings.bp)

    # Register main route
    from app.routes import main
    app.register_blueprint(main.bp)

    return app
