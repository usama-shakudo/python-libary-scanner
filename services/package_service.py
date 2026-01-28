"""
Package service for business logic
"""

import logging
import requests
from typing import Optional, Tuple
from repositories.package_repository import PackageRepository
from config import Config

logger = logging.getLogger(__name__)


class PackageService:
    """Service for package business logic"""

    def __init__(self, package_repo: PackageRepository):
        self.package_repo = package_repo

    def check_pypi_availability(self, package_name: str) -> Tuple[bool, Optional[bytes], Optional[dict]]:
        """
        Check if package exists on PyPI server

        Returns:
            (True, content, headers) - Package available on PyPI
            (False, None, None) - Package not available
        """
        try:
            pypi_url = f"{Config.PYPI_SERVER_URL}/simple/{package_name}/"
            response = requests.get(pypi_url, timeout=10)

            if response.status_code == 200:
                return (True, response.content, dict(response.headers))

            return (False, None, None)

        except requests.RequestException as e:
            logger.warning(f"PyPI server check failed: {e}")
            return (False, None, None)

    def check_package_status(self, package_name: str) -> Tuple[str, Optional[dict]]:
        """
        Check package status in database

        Returns:
            ('safe', None) - Package is safe to use
            ('vulnerable', info) - Package has vulnerabilities
            ('pending', None) - Package is being scanned
            ('unknown', None) - Package not in database
        """
        package = self.package_repo.find_by_name(package_name)

        if not package:
            return ('unknown', None)

        return (package.status, package.vulnerability_info)

    def add_package_for_scanning(self, package_name: str) -> bool:
        """Add new package for scanning"""
        try:
            package = self.package_repo.create(package_name, status='pending')
            if package:
                logger.info(f"Added package for scanning: {package_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding package: {e}")
            return False

    def get_pending_packages(self, limit: int = 10) -> list:
        """Get pending packages for scanning"""
        try:
            packages = self.package_repo.find_pending(limit)
            return [pkg.package_name for pkg in packages]
        except Exception as e:
            logger.error(f"Error fetching pending packages: {e}")
            return []

    def update_scan_result(
        self, package_name: str, is_safe: bool, vulnerability_info: dict = None
    ) -> bool:
        """Update package scan result"""
        try:
            status = 'safe' if is_safe else 'vulnerable'
            success = self.package_repo.update_status(
                package_name, status, vulnerability_info
            )
            if success:
                logger.info(f"Updated package {package_name}: {status}")
            return success
        except Exception as e:
            logger.error(f"Error updating scan result: {e}")
            return False
