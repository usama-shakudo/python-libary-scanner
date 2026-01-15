from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Custom PyPI Server URL
PYPI_SERVER_URL = "https://pypiserver.umang-shakudo.canopyhub.io"

@app.route('/')
def home():
    """Root endpoint with API information"""
    return jsonify({
        "message": "Python Library Scanner API",
        "version": "1.0.0",
        "endpoints": {
            "/api/package/<package_name>": "Get details about a specific package",
            "/api/package/<package_name>/versions": "Get all versions of a package",
            "/api/search?q=<query>": "Search for packages",
            "/health": "Health check endpoint"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/api/package/<package_name>')
def get_package_info(package_name: str):
    """
    Get detailed information about a specific Python package from PyPI
    """
    try:
        # Proxy request to PyPI API
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
        logger.info(f"Response data: {data}")

        # Extract relevant information
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

@app.route('/api/package/<package_name>/versions')
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

@app.route('/api/search')
def search_packages():
    """
    Search for Python packages
    Note: PyPI deprecated their XML-RPC search API, so we'll use a simple approach
    """
    query = request.args.get('q', '')

    if not query:
        return jsonify({
            "error": "Query parameter 'q' is required"
        }), 400

    try:
        # Try to get package info directly if exact match
        url = f"{PYPI_SERVER_URL}/{query}/json"
        logger.info(f"Searching for package: {url}")
        response = requests.get(url, timeout=10)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            logger.info(f"Found package: {query}")
            info = data.get('info', {})

            return jsonify({
                "query": query,
                "results": [{
                    "name": info.get('name'),
                    "version": info.get('version'),
                    "summary": info.get('summary'),
                    "package_url": info.get('package_url'),
                }]
            }), 200
        else:
            logger.info(f"Package not found: {query}")
            return jsonify({
                "query": query,
                "results": [],
                "message": "No exact match found. Consider using the package name directly at /api/package/<name>"
            }), 200

    except requests.RequestException as e:
        logger.error(f"Search failed for {query}: {str(e)}")
        return jsonify({
            "error": "Search failed",
            "details": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error",
        "message": str(error)
    }), 500

if __name__ == '__main__':
    logger.info(f"Starting Flask app with PyPI server: {PYPI_SERVER_URL}")
    app.run(debug=True, host='0.0.0.0', port=5000)
