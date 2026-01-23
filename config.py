"""
Configuration settings for the Python Library Scanner API
"""

import os

# PyPI Server Configuration
PYPI_SERVER_URL = os.getenv(
    'PYPI_SERVER_URL',
    'http://pypiserver.hyperplane-pypiserver.svc.cluster.local:8080'
)

# Flask Configuration
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Database Configuration (PostgreSQL/Supabase)
DB_HOST = os.getenv('DB_HOST', 'supabase-postgresql.hyperplane-supabase.svc.cluster.local')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'supabase_admin')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')  # Set via environment variable for security

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
