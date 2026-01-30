"""
Package repository for database operations
"""

import logging
from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.package import Package
from flask import g

logger = logging.getLogger(__name__)


class PackageRepository:
    """Repository for package database operations"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        db_session: Optional, defaults to per-request session g.db
        """
        self.db = db_session or g.db

    def find_by_name(self, package_name: str) -> Optional[Package]:
        """Find package by name (returns latest version or first match)"""
        try:
            return self.db.query(Package).filter(
                Package.package_name == package_name
            ).order_by(Package.created_at.desc()).first()
        except Exception as e:
            logger.error(f"Error finding package '{package_name}': {e}", exc_info=True)
            return None

    def find_by_name_and_version(self, package_name: str, version: Optional[str]) -> Optional[Package]:
        """Find package by name and version"""
        try:
            query = self.db.query(Package).filter(Package.package_name == package_name)

            if version:
                query = query.filter(Package.version == version)
            else:
                # If no version specified, look for "latest" or None
                query = query.filter(
                    (Package.version == "latest") | (Package.version.is_(None))
                )

            return query.first()
        except Exception as e:
            logger.error(f"Error finding package '{package_name}' version '{version}': {e}", exc_info=True)
            return None

    def create(
        self,
        package_name: str,
        version: Optional[str] = None,
        python_version: Optional[str] = None,
        status: str = 'pending'
    ) -> Optional[Package]:
        """Create new package with version information"""
        try:
            package = Package(
                package_name=package_name,
                version=version or "latest",
                python_version=python_version,
                status=status
            )
            self.db.add(package)
            self.db.commit()
            self.db.refresh(package)
            return package
        except IntegrityError:
            self.db.rollback()
            logger.warning(f"Package already exists: {package_name}=={version}")
            return self.find_by_name_and_version(package_name, version)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating package '{package_name}=={version}': {e}", exc_info=True)
            return None

    def update_status(
        self, package_name: str, status: str, vulnerability_info: dict = None
    ) -> bool:
        """Update package status"""
        try:
            package = self.find_by_name(package_name)
            if not package:
                return False

            package.status = status
            if vulnerability_info is not None:
                package.vulnerability_info = vulnerability_info

            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating package '{package_name}': {e}", exc_info=True)
            return False

    def find_pending(self, limit: int = 10) -> List[Package]:
        """Find pending packages"""
        try:
            return self.db.query(Package).filter(
                Package.status == 'pending'
            ).order_by(Package.created_at.asc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error fetching pending packages: {e}", exc_info=True)
            return []

    def count_by_status(self, status: str) -> int:
        """Count packages by status"""
        try:
            return self.db.query(Package).filter(
                Package.status == status
            ).count()
        except Exception as e:
            logger.error(f"Error counting packages by status '{status}': {e}", exc_info=True)
            return 0

    def find_all(self, limit: Optional[int] = None) -> List[Package]:
        """Find all packages"""
        try:
            query = self.db.query(Package).order_by(Package.created_at.desc())
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error fetching all packages: {e}", exc_info=True)
            return []

    def get_status_stats(self) -> dict:
        """Get package count statistics by status"""
        try:
            # Get counts by status
            results = self.db.query(
                Package.status,
                func.count(Package.id).label('count')
            ).group_by(Package.status).all()

            stats = {row.status: row.count for row in results}

            # Get total count
            total = self.db.query(func.count(Package.id)).scalar()

            return {
                'total': total or 0,
                'by_status': stats
            }
        except Exception as e:
            logger.error(f"Error getting status stats: {e}", exc_info=True)
            return {'total': 0, 'by_status': {}}
