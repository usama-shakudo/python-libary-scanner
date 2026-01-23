"""
Health check routes
"""

from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        "service": "Python Library Scanner API",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "package_info": "/api/package/<package_name>",
            "package_versions": "/api/package/<package_name>/versions",
            "simple_api": "/simple/<package_name>/",
            "package_download": "/packages/<filename>"
        }
    }), 200


@health_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Python Library Scanner API"
    }), 200
