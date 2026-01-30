"""
Application configuration - Loads from environment variables
"""

import os
import logging
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()


class Config:
    """Application configuration"""

    # Flask
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_ENV = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_FLASK_ENV', 'production')

    # Database
    SUPABASE_DATABASE_URL = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_SUPABASE_DATABASE_URL')
    DATABASE_URL = SUPABASE_DATABASE_URL  # Alias for backward compatibility
    SQLALCHEMY_DATABASE_URI = SUPABASE_DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = FLASK_ENV == 'development'

    # PyPI Server
    PYPI_SERVER_URL = os.getenv(
        'HYPERPLANE_CUSTOM_SECRET_KEY_PYPI_SERVER_URL',
        'http://pypiserver-pypiserver.hyperplane-pypiserver.svc.cluster.local:8080'
    )
    PYPI_USERNAME = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_PYPI_USERNAME')
    PYPI_PASSWORD = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_PYPI_PASSWORD')

    # Hyperplane API
    HYPERPLANE_GRAPHQL_URL = os.getenv(
        'HYPERPLANE_CUSTOM_SECRET_KEY_HYPERPLANE_GRAPHQL_URL',
        'http://api-server.hyperplane-core.svc.cluster.local/graphql'
    )
    HYPERPLANE_DOMAIN = os.getenv('HYPERPLANE_DOMAIN')
    HYPERPLANE_REALM = os.getenv('HYPERPLANE_REALM', 'Hyperplane')
    HYPERPLANE_CLIENT_ID = os.getenv('HYPERPLANE_CLIENT_ID', 'istio')

    # Authentication
    HYPERPLANE_USERNAME = os.getenv('HYPERPLANE_USERNAME')
    HYPERPLANE_PASSWORD = os.getenv('HYPERPLANE_PASSWORD')
    HYPERPLANE_REFRESH_TOKEN = os.getenv('HYPERPLANE_REFRESH_TOKEN')

    # User Information
    HYPERPLANE_USER_ID = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_HYPERPLANE_USER_ID')
    HYPERPLANE_USER_EMAIL = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_HYPERPLANE_USER_EMAIL')
    HYPERPLANE_VC_SERVER_ID = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_HYPERPLANE_VC_SERVER_ID')

    # Scanner
    SCANNER_IMAGE = os.getenv(
        'HYPERPLANE_CUSTOM_SECRET_KEY_SCANNER_IMAGE',
        'gcr.io/devsentient-infra/custom/hnb/custom/pypiscanningjob:latest'
    )
    PYTHON_VERSIONS = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_PYTHON_VERSIONS', '3.9 3.10 3.11 3.12')
    MAX_CONCURRENT_JOBS = int(os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_MAX_CONCURRENT_JOBS', '10'))

    # Logging
    LOG_LEVEL = os.getenv('HYPERPLANE_CUSTOM_SECRET_KEY_LOG_LEVEL', 'INFO')

    @classmethod
    def init_logging(cls):
        """Initialize logging configuration"""
        level = getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = ['SUPABASE_DATABASE_URL', 'PYPI_SERVER_URL']
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
