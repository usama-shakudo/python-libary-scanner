"""
Package controller for handling HTTP requests
"""

import logging
from flask import Response, jsonify
from services.package_service import PackageService
from repositories.package_repository import PackageRepository
from flask import g

logger = logging.getLogger(__name__)


class PackageController:
    """Controller for package-related requests"""

    def __init__(self, package_service: PackageService = None):
        """
        Initialize controller.
        Optionally inject service for testing.
        """
        self.package_service = package_service

    @staticmethod
    def create_with_db() -> "PackageController":
        """
        Factory method to create controller with current request DB session.
        """
        package_repo = PackageRepository(g.db)
        package_service = PackageService(package_repo)
        return PackageController(package_service)

    def get_package(self, package_name: str) -> Response:
        """
        Get package - checks PyPI server first, then database.

        Returns:
            200 - Package available on PyPI (pass-through)
            403 - Package is vulnerable
            503 - Package is pending scan
        """
        try:
            # Check PyPI server first
            available, content, headers = self.package_service.check_pypi_availability(package_name)

            if available:
                return Response(content, status=200, headers=headers)

            # Not on PyPI - check database for status
            status, vuln_info = self.package_service.check_package_status(package_name)

            #TODO: Move status to an enum
            if status == 'safe':
                # Safe but pending scan
                return self._respond_pending(package_name)

            elif status == 'vulnerable':
                return self._respond_vulnerable(package_name, vuln_info)

            elif status == 'pending':
                return self._respond_pending(package_name)

            else:  # unknown
                self.package_service.add_package_for_scanning(package_name)
                return self._respond_pending(package_name)

        except Exception as e:
            logger.error(f"Error processing request for '{package_name}': {e}", exc_info=True)
            return self._respond_error()

    # -----------------------
    # Response helpers
    # -----------------------

    def _respond_vulnerable(self, package_name: str, vuln_info: dict) -> Response:
        """Return 403 Forbidden for vulnerable package"""
        problem_details = {
            "type": "https://pypi.org/security/vulnerability-detected",
            "title": "Package Vulnerability Detected",
            "status": 403,
            "detail": f"The package '{package_name}' contains known security vulnerabilities and cannot be installed.",
            "instance": f"/simple/{package_name}/",
            "vulnerabilities": vuln_info or {}
        }

        return jsonify(problem_details), 403, {
            'Content-Type': 'application/problem+json'
        }

    def _respond_pending(self, package_name: str) -> Response:
        """Return 503 Service Unavailable for pending scan"""
        problem_details = {
            "type": "https://pypi.org/security/scan-in-progress",
            "title": "Security Scan In Progress",
            "status": 503,
            "detail": f"The package '{package_name}' is currently being scanned for vulnerabilities. Please try again in a few minutes.",
            "instance": f"/simple/{package_name}/"
        }

        return jsonify(problem_details), 503, {
            'Content-Type': 'application/problem+json',
            'Retry-After': '300'  # 5 minutes
        }

    def _respond_error(self) -> Response:
        """Return 500 Internal Server Error"""
        problem_details = {
            "type": "https://pypi.org/errors/internal-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred while processing your request."
        }

        return jsonify(problem_details), 500, {
            'Content-Type': 'application/problem+json'
        }
