"""
JSON API routes for package information
"""

from flask import Blueprint, jsonify, request
import requests
import logging

from config import Config
from controllers.package_controller import PackageController

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


@api_bp.route('/package/<package_name>')
def get_package_info(package_name: str):
    """
    Get detailed information about a Python package
    """
    try:
        url = f"{Config.PYPI_SERVER_URL}/{package_name}/json"
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
        url = f"{Config.PYPI_SERVER_URL}/{package_name}/json"
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
    List all packages in database
    """
    controller = PackageController.create_with_db()
    return controller.list_all_packages()


@api_bp.route('/db/packages/pending')
def list_pending_packages():
    """
    List only pending packages in database
    """
    controller = PackageController.create_with_db()
    return controller.list_pending_packages()


@api_bp.route('/db/packages/stats')
def get_package_stats():
    """
    Get statistics about packages by status
    """
    controller = PackageController.create_with_db()
    return controller.get_package_stats()


@api_bp.route('/pypi/packages')
def list_pypi_packages():
    """
    List all packages available in internal PyPI server
    """
    controller = PackageController.create_with_db()
    return controller.list_pypi_packages()
