"""
JSON API routes for package information
"""

from flask import Blueprint, jsonify, request
import requests
import logging

from config import PYPI_SERVER_URL

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


@api_bp.route('/package/<package_name>')
def get_package_info(package_name: str):
    """
    Get detailed information about a Python package
    """
    try:
        url = f"{PYPI_SERVER_URL}/{package_name}/json"
        logger.info(f"Requesting package info: {url}")
        response = requests.get(url, timeout=10)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.status_code == 404:
            logger.warning(f"Package not found: {package_name}")
            return jsonify({
                "error": "Package not found",
                "package_name": package_name
            }), 404

        response.raise_for_status()
        data = response.json()
        logger.info(f"Response data keys: {list(data.keys())}")

        info = data.get('info', {})
        result = {
            "name": info.get('name'),
            "version": info.get('version'),
            "summary": info.get('summary'),
            "description": info.get('description'),
            "author": info.get('author'),
            "author_email": info.get('author_email'),
            "license": info.get('license'),
            "home_page": info.get('home_page'),
            "project_url": info.get('project_url'),
            "package_url": info.get('package_url'),
            "requires_python": info.get('requires_python'),
            "keywords": info.get('keywords'),
        }

        return jsonify(result), 200

    except requests.RequestException as e:
        logger.error(f"Failed to fetch package info for {package_name}: {str(e)}")
        return jsonify({
            "error": "Failed to fetch package information",
            "details": str(e)
        }), 500


@api_bp.route('/package/<package_name>/versions')
def get_package_versions(package_name: str):
    """
    Get all available versions of a Python package
    """
    try:
        url = f"{PYPI_SERVER_URL}/{package_name}/json"
        logger.info(f"Requesting package versions: {url}")
        response = requests.get(url, timeout=10)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.status_code == 404:
            logger.warning(f"Package not found: {package_name}")
            return jsonify({
                "error": "Package not found",
                "package_name": package_name
            }), 404

        response.raise_for_status()
        data = response.json()
        logger.info(f"Response data keys: {list(data.keys())}")

        releases = data.get('releases', {})
        versions = list(releases.keys())

        result = {
            "package_name": package_name,
            "total_versions": len(versions),
            "versions": sorted(versions, reverse=True),
            "latest_version": data.get('info', {}).get('version')
        }

        return jsonify(result), 200

    except requests.RequestException as e:
        logger.error(f"Failed to fetch package versions for {package_name}: {str(e)}")
        return jsonify({
            "error": "Failed to fetch package versions",
            "details": str(e)
        }), 500


@api_bp.route('/search')
def search_packages():
    """
    Search for Python packages
    Note: Basic implementation, can be enhanced with actual search functionality
    """
    query = request.args.get('q', '')

    if not query:
        return jsonify({
            "error": "Missing search query",
            "message": "Please provide a search query using the 'q' parameter"
        }), 400

    return jsonify({
        "query": query,
        "results": [],
        "message": "Search functionality not fully implemented yet"
    }), 200


@api_bp.route('/db/packages')
def list_db_packages():
    """
    List all packages in database (for debugging)
    """
    from services import get_database_service
    from psycopg2.extras import RealDictCursor

    db_service = get_database_service()
    if not db_service:
        return jsonify({
            "error": "Database not available",
            "message": "Database service not initialized"
        }), 503

    try:
        with db_service.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT package_name, status, vulnerability_info,
                           created_at, updated_at
                    FROM packages
                    ORDER BY created_at DESC
                """)
                packages = cursor.fetchall()

                # Convert to JSON-serializable format
                result = []
                for pkg in packages:
                    result.append({
                        "package_name": pkg['package_name'],
                        "status": pkg['status'],
                        "vulnerability_info": pkg['vulnerability_info'],
                        "created_at": pkg['created_at'].isoformat() if pkg['created_at'] else None,
                        "updated_at": pkg['updated_at'].isoformat() if pkg['updated_at'] else None
                    })

                return jsonify({
                    "total": len(result),
                    "packages": result
                }), 200

    except Exception as e:
        logger.error(f"Error fetching packages from DB: {str(e)}")
        return jsonify({
            "error": "Database query failed",
            "details": str(e)
        }), 500
