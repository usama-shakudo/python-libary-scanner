"""
Routes package initialization
Exports all blueprints
"""

from .health import health_bp
from .simple_api import simple_api_bp
from .packages import packages_bp
from .api import api_bp

__all__ = ['health_bp', 'simple_api_bp', 'packages_bp', 'api_bp']
