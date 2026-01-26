"""
Python Library Scanner API
Main Flask application entry point
"""

from flask import Flask
from flask_cors import CORS
import logging

from config import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG, LOG_LEVEL, LOG_FORMAT, PYPI_SERVER_URL,
    DATABASE_URL
)
from routes import health_bp, simple_api_bp, packages_bp, api_bp
from services import init_database_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)

# Enable CORS
CORS(app)
DATABASE_URL = 'postgresql://supabase_admin:CYo8ILCGUi%@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres'
# Initialize database service
try:
    init_database_service(DATABASE_URL)
    logger.info("Database service initialized with Supabase URL (overriding ConfigMap)")
except Exception as e:
    logger.error(f"Failed to initialize database service: {str(e)}")

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(simple_api_bp)
app.register_blueprint(packages_bp)
app.register_blueprint(api_bp)

if __name__ == '__main__':
    logger.info(f"Starting Flask app with PyPI server: {PYPI_SERVER_URL}")
    logger.info(f"Server will run on {FLASK_HOST}:{FLASK_PORT}")
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT)
