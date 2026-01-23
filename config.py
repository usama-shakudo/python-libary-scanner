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
# Use connection string format: postgresql://user:password@host:port/database
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://supabase_admin:@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres'
)

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
