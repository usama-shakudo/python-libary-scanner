from flask import Flask, jsonify, request, Response, redirect
from flask_cors import CORS
import requests
import logging
from typing import Dict, Any
from stub_generator import generate_scanning_stub

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Custom PyPI Server URL (using internal Kubernetes service)
# Internal service format: <service-name>.<namespace>.svc.cluster.local:<port>
PYPI_SERVER_URL = "http://pypiserver.hyperplane-pypiserver.svc.cluster.local:8080"

@app.route('/simple/<package_name>/')
def simple_package(package_name: str):
    """
    Simple Repository API - Package Links
    Returns download links for a specific package (for pip)
    Uses RFC 9457 Problem Details for error responses
    """
    try:
        # Log all incoming request headers from pip
        logger.info(f"=== Incoming Request from pip ===")
        logger.info(f"Package: {package_name}")
        logger.info(f"Request Headers: {dict(request.headers)}")
        logger.info(f"Request Method: {request.method}")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request Remote Address: {request.remote_addr}")

        url = f"{PYPI_SERVER_URL}/simple/{package_name}/"
        logger.info(f"Proxying to: {url}")
        response = requests.get(url, timeout=10)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response content preview: {response.text[:500]}")

        if response.status_code == 404:
            logger.warning(f"Package not found, scanning in progress: {package_name}")

            # RFC 9457 Problem Details for modern tools (uv, future pip)
            problem_details = {
                "type": "about:blank",
                "title": "Package Scanning in Progress",
                "status": 503,
                "detail": f"Package '{package_name}' is currently being scanned and will be available soon. Please try again in 2-3 minutes.",
                "instance": f"/simple/{package_name}/"
            }

            # Return RFC 9457 compliant response
            # Modern tools like uv will display the 'detail' field
            # Legacy pip will ignore it but see the 503 status
            return jsonify(problem_details), 503, {
                'Content-Type': 'application/problem+json',
                'Retry-After': '30'  # 30 seconds for faster testing
            }

        response.raise_for_status()

        # Return the HTML response as-is (Simple API format)
        return Response(response.content, mimetype='text/html')

    except requests.RequestException as e:
        logger.error(f"Failed to fetch package links for {package_name}: {str(e)}")

        # RFC 9457 error response
        problem_details = {
            "type": "about:blank",
            "title": "Package Fetch Error",
            "status": 500,
            "detail": f"Failed to fetch package information: {str(e)}",
            "instance": f"/simple/{package_name}/"
        }

        return jsonify(problem_details), 500, {'Content-Type': 'application/problem+json'}

