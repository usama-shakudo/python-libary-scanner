"""
Package controller for handling HTTP requests
"""

import logging
from typing import Optional
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

    def get_package(
        self,
        package_name: str,
        version: Optional[str] = None,
        python_version: Optional[str] = None
    ) -> Response:
        """
        Get package - checks PyPI server first, then database.

        Args:
            package_name: Name of the package
            version: Version of the package (optional)
            python_version: Python version from pip User-Agent (optional)

        Returns:
            200 - Package available on PyPI (pass-through)
            403 - Package is vulnerable
            503 - Package is pending scan or being scanned
        """
        try:
            # Check PyPI server first
            available, content, headers = self.package_service.check_pypi_availability(package_name)

            if available:
                return Response(content, status=200, headers=headers)

            # Not on PyPI - check database for status
            status, vuln_info = self.package_service.check_package_status(package_name, version)

            # Use enum values
            from models.package import PackageStatus

            if status == PackageStatus.COMPLETED.value:
                # Package scanned and uploaded to internal PyPI
                return Response(content, status=200, headers=headers)

            elif status == PackageStatus.VULNERABLE.value:
                return self._respond_vulnerable(package_name, vuln_info)

            elif status in [PackageStatus.PENDING.value, PackageStatus.DOWNLOADED.value]:
                return self._respond_pending(package_name)

            else:  # unknown or error states
                # Add package for scanning with version info
                self.package_service.add_package_for_scanning(
                    package_name, version, python_version
                )
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

    # -----------------------
    # API endpoints for package information
    # -----------------------

    def list_all_packages(self) -> Response:
        """List all packages in database"""
        try:
            packages = self.package_service.get_all_packages()
            return jsonify({
                "total": len(packages),
                "packages": packages
            }), 200
        except Exception as e:
            logger.error(f"Error listing packages: {e}", exc_info=True)
            return jsonify({
                "error": "Failed to fetch packages",
                "details": str(e)
            }), 500

    def list_pending_packages(self) -> Response:
        """List pending packages"""
        try:
            packages = self.package_service.get_pending_packages_detailed()
            return jsonify({
                "total": len(packages),
                "packages": packages
            }), 200
        except Exception as e:
            logger.error(f"Error listing pending packages: {e}", exc_info=True)
            return jsonify({
                "error": "Failed to fetch pending packages",
                "details": str(e)
            }), 500

    def get_package_stats(self) -> Response:
        """Get package statistics"""
        try:
            stats = self.package_service.get_package_stats()
            return jsonify(stats), 200
        except Exception as e:
            logger.error(f"Error getting package stats: {e}", exc_info=True)
            return jsonify({
                "error": "Failed to fetch statistics",
                "details": str(e)
            }), 500

    def list_pypi_packages(self) -> Response:
        """List packages from PyPI server"""
        try:
            success, packages, error = self.package_service.get_pypi_packages()

            if not success:
                return jsonify({
                    "error": "Failed to fetch PyPI packages",
                    "details": error
                }), 502

            return jsonify({
                "total": len(packages),
                "packages": packages
            }), 200
        except Exception as e:
            logger.error(f"Error listing PyPI packages: {e}", exc_info=True)
            return jsonify({
                "error": "Internal server error",
                "details": str(e)
            }), 500
