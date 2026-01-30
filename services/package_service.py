"""
Package service for business logic
"""

import logging
import requests
from typing import Optional, Tuple
from repositories.package_repository import PackageRepository
from config import Config

try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False

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
            logger.info(f"🔍 Checking internal PyPI: {pypi_url}")

            response = requests.get(pypi_url, timeout=10)

            logger.info(f"📥 PyPI Response - Status: {response.status_code}")
            logger.info(f"📥 PyPI Response - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            logger.info(f"📥 PyPI Response - Content-Length: {len(response.content)} bytes")

            if response.status_code == 200:
                # Log first 1000 chars of HTML content for debugging
                content_preview = response.text[:1000] if len(response.text) > 1000 else response.text
                logger.info(f"📄 PyPI Response - Content preview:\n{content_preview}")
                logger.info(f"✅ Package '{package_name}' found on internal PyPI")
                return (True, response.content, dict(response.headers))

            logger.info(f"❌ Package '{package_name}' not found on internal PyPI (status: {response.status_code})")
            return (False, None, None)

        except requests.RequestException as e:
            logger.warning(f"⚠️  PyPI server check failed for '{package_name}': {e}")
            return (False, None, None)

    def check_package_status(
        self, package_name: str, version: Optional[str] = None
    ) -> Tuple[str, Optional[dict]]:
        """
        Check package status in database

        Args:
            package_name: Name of the package
            version: Version of the package (None for latest)

        Returns:
            ('completed', None) - Package is safe and uploaded
            ('vulnerable', info) - Package has vulnerabilities
            ('pending', None) - Package is being scanned
            ('unknown', None) - Package not in database
        """
        package = self.package_repo.find_by_name_and_version(package_name, version)

        if not package:
            return ('unknown', None)

        return (package.status, package.vulnerability_info)

    def add_package_for_scanning(
        self,
        package_name: str,
        version: Optional[str] = None,
        python_version: Optional[str] = None
    ) -> bool:
        """Add new package for scanning with version information"""
        try:
            package = self.package_repo.create(
                package_name=package_name,
                version=version,
                python_version=python_version,
                status='pending'
            )
            if package:
                version_str = f"=={version}" if version else ""
                logger.info(f"Added package for scanning: {package_name}{version_str}")
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

    def get_all_packages(self, limit: int = None) -> list:
        """Get all packages from database"""
        try:
            packages = self.package_repo.find_all(limit)
            return [pkg.to_dict() for pkg in packages]
        except Exception as e:
            logger.error(f"Error fetching all packages: {e}")
            return []

    def get_package_stats(self) -> dict:
        """Get package statistics"""
        try:
            return self.package_repo.get_status_stats()
        except Exception as e:
            logger.error(f"Error getting package stats: {e}")
            return {'total': 0, 'by_status': {}}

    def get_pending_packages_detailed(self) -> list:
        """Get detailed pending packages"""
        try:
            packages = self.package_repo.find_pending(limit=100)
            return [pkg.to_dict() for pkg in packages]
        except Exception as e:
            logger.error(f"Error fetching pending packages: {e}")
            return []

    def get_pypi_packages(self) -> Tuple[bool, Optional[list], Optional[str]]:
        """
        Get list of packages from PyPI server

        Returns:
            (True, packages_list, None) - Success
            (False, None, error_message) - Failure
        """
        if not HAS_BEAUTIFULSOUP:
            return (False, None, "beautifulsoup4 library is not installed")

        try:
            simple_url = f"{Config.PYPI_SERVER_URL}/simple/"

            # Prepare auth if available
            auth = None
            if Config.PYPI_USERNAME and Config.PYPI_PASSWORD:
                auth = (Config.PYPI_USERNAME, Config.PYPI_PASSWORD)

            # Fetch the simple index
            response = requests.get(simple_url, auth=auth, timeout=10)

            if response.status_code != 200:
                return (False, None, f"PyPI server returned status {response.status_code}")

            # Parse HTML to get package list
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a')

            # Extract package names
            packages = []
            for link in links:
                package_name = link.text.strip()
                if package_name:
                    packages.append(package_name)

            # Sort packages alphabetically
            packages.sort()

            return (True, packages, None)

        except requests.RequestException as e:
            logger.error(f"Failed to fetch PyPI packages: {e}")
            return (False, None, f"Failed to connect to PyPI server: {str(e)}")
        except Exception as e:
            logger.error(f"Error listing PyPI packages: {e}")
            return (False, None, f"Internal error: {str(e)}")
