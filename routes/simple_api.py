"""
PyPI Simple Repository API routes (PEP 503)
Handles pip package resolution with RFC 9457 Problem Details support
"""

from flask import Blueprint, request, Response, jsonify
import requests
import logging

from config import PYPI_SERVER_URL

simple_api_bp = Blueprint('simple_api', __name__, url_prefix='/simple')
logger = logging.getLogger(__name__)


@simple_api_bp.route('/<package_name>/')
def simple_package(package_name: str):
    """
    Simple Repository API - Package Links
    Returns download links for a specific package (for pip)
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
            # Legacy pip will see the 503 status and retry
            return jsonify(problem_details), 503, {
                'Content-Type': 'application/problem+json',
                'Retry-After': '180'  # 3 minutes
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
