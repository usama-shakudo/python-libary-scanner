from flask import Flask, jsonify, request, Response, redirect
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
        "pypi_server": PYPI_SERVER_URL,
        "endpoints": {
            "/simple/": "Package index (for pip)",
            "/simple/<package_name>/": "Package download links (for pip)",
            "/packages/<path>": "Package file download (for pip)",
            "/api/package/<package_name>": "Get details about a specific package",
            "/api/package/<package_name>/versions": "Get all versions of a package",
            "/api/search?q=<query>": "Search for packages",
            "/health": "Health check endpoint"
        },
        "pip_usage": "pip install --index-url http://localhost:5000/simple/ <package_name>"
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

@app.route('/simple/')
def simple_index():
    """
    Simple Repository API - Package Index
    Lists all available packages (for pip)
    """
    try:
        logger.info(f"Requesting package index from: {PYPI_SERVER_URL}/simple/")
        response = requests.get(f"{PYPI_SERVER_URL}/simple/", timeout=10)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            # Return the HTML response as-is (Simple API format)
            return Response(response.content, mimetype='text/html')
        else:
            logger.warning(f"Failed to fetch package index: {response.status_code}")
            return Response("<html><body><h1>Package Index Unavailable</h1></body></html>",
                          mimetype='text/html', status=response.status_code)

    except requests.RequestException as e:
        logger.error(f"Failed to fetch package index: {str(e)}")
        return Response("<html><body><h1>Error fetching package index</h1></body></html>",
                      mimetype='text/html', status=500)

@app.route('/simple/<package_name>/')
def simple_package(package_name: str):
    """
    Simple Repository API - Package Links
    Returns download links for a specific package (for pip)
    """
    try:
        url = f"{PYPI_SERVER_URL}/simple/{package_name}/"
        logger.info(f"Requesting package links: {url}")
        response = requests.get(url, timeout=10)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response content preview: {response.text[:500]}")

        if response.status_code == 404:
            logger.warning(f"Package not found: {package_name}")
            return Response(f"<html><body><h1>404 Not Found: {package_name}</h1></body></html>",
                          mimetype='text/html', status=404)

        response.raise_for_status()

        # Return the HTML response as-is (Simple API format)
        return Response(response.content, mimetype='text/html')

    except requests.RequestException as e:
        logger.error(f"Failed to fetch package links for {package_name}: {str(e)}")
        return Response(f"<html><body><h1>Error: {str(e)}</h1></body></html>",
                      mimetype='text/html', status=500)

@app.route('/packages/<path:filename>')
def download_package(filename: str):
    """
    Package file download endpoint
    Proxies package file downloads from the PyPI server
    """
    try:
        url = f"{PYPI_SERVER_URL}/packages/{filename}"
        logger.info(f"Downloading package file: {url}")

        response = requests.get(url, stream=True, timeout=30)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.status_code == 404:
            logger.warning(f"Package file not found: {filename}")
            return Response("File not found", status=404)

        response.raise_for_status()

        # Stream the file back to the client
        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get('content-type', 'application/octet-stream'),
            headers={
                'Content-Disposition': response.headers.get('content-disposition', ''),
                'Content-Length': response.headers.get('content-length', '')
            }
        )

    except requests.RequestException as e:
        logger.error(f"Failed to download package file {filename}: {str(e)}")
        return Response(f"Error downloading file: {str(e)}", status=500)

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
