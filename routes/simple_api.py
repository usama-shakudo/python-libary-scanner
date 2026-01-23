"""
PyPI Simple Repository API routes (PEP 503)
Handles pip package resolution with RFC 9457 Problem Details support
"""

from flask import Blueprint, request, Response, jsonify
import requests
import logging

from config import PYPI_SERVER_URL
from services import get_database_service

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
            logger.warning(f"Package not found in PyPI: {package_name}")

            # Check database for vulnerability status
            db_service = get_database_service()
            if db_service:
                package_data = db_service.get_package_status(package_name)

                if package_data:
                    # Package exists in database
                    if db_service.is_package_vulnerable(package_data):
                        # Package is vulnerable - block installation
                        logger.error(f"Package is vulnerable: {package_name}")
                        vuln_info = db_service.get_vulnerability_info(package_data)

                        problem_details = {
                            "type": "about:blank",
                            "title": "Security Policy Violation",
                            "status": 403,
                            "detail": f"Package '{package_name}' is blocked due to security vulnerabilities. {vuln_info}",
                            "instance": f"/simple/{package_name}/"
                        }

                        return jsonify(problem_details), 403, {
                            'Content-Type': 'application/problem+json'
                        }
                    else:
                        # Package is pending/scanning
                        logger.info(f"Package is being scanned: {package_name}")
                        problem_details = {
                            "type": "about:blank",
                            "title": "Package Scanning in Progress",
                            "status": 503,
                            "detail": f"Package '{package_name}' is currently being scanned and will be available soon. Please try again in 2-3 minutes.",
                            "instance": f"/simple/{package_name}/"
                        }

                        return jsonify(problem_details), 503, {
                            'Content-Type': 'application/problem+json',
                            'Retry-After': '180'  # 3 minutes
                        }
                else:
                    # Package not in database - add as pending
                    logger.info(f"Package not in database, adding as pending: {package_name}")
                    db_service.add_package_pending(package_name)

                    problem_details = {
                        "type": "about:blank",
                        "title": "Package Scanning Initiated",
                        "status": 503,
                        "detail": f"Package '{package_name}' has been queued for security scanning. Please try again in 2-3 minutes.",
                        "instance": f"/simple/{package_name}/"
                    }

                    return jsonify(problem_details), 503, {
                        'Content-Type': 'application/problem+json',
                        'Retry-After': '180'  # 3 minutes
                    }
            else:
                # Database not available - return generic scanning message
                logger.warning("Database service not available")
                problem_details = {
                    "type": "about:blank",
                    "title": "Package Scanning in Progress",
                    "status": 503,
                    "detail": f"Package '{package_name}' is currently being scanned. Please try again in 2-3 minutes.",
                    "instance": f"/simple/{package_name}/"
                }

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
