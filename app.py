"""
Python Library Scanner API - Refactored
Main Flask application with clean architecture
"""

import logging
from flask import Flask
from flask_cors import CORS

from config import Config
from database import init_database, close_database
from routes.simple_api import simple_api_bp

# Initialize logging
Config.init_logging()
logger = logging.getLogger(__name__)


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS
    CORS(app)

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    # Initialize database
    if not init_database():
        logger.error("Failed to initialize database")
        raise RuntimeError("Database initialization failed")

    # Register blueprints
    app.register_blueprint(simple_api_bp)

    # Register cleanup with error logging
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            logger.error(f"App context teardown error: {exception}")
        close_database()

    logger.info("Application initialized successfully")
    return app


# Only initialize app when not running as main (for tests/CLI)
if __name__ != '__main__':
    app = create_app()
else:
    # Running as main - create app and start server
    logger.info(f"Starting server on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    logger.info(f"PyPI Server: {Config.PYPI_SERVER_URL}")
    logger.info(f"Environment: {Config.FLASK_ENV}")

    app = create_app()
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=(Config.FLASK_ENV == 'development')
    )
