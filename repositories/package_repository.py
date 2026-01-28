"""
Package repository for database operations
"""

import logging
from typing import Optional, List
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
        """Find package by name"""
        try:
            return self.db.query(Package).filter(
                Package.package_name == package_name
            ).first()
        except Exception as e:
            logger.error(f"Error finding package '{package_name}': {e}", exc_info=True)
            return None

    def create(self, package_name: str, status: str = 'pending') -> Optional[Package]:
        """Create new package"""
        try:
            package = Package(package_name=package_name, status=status)
            self.db.add(package)
            self.db.commit()
            self.db.refresh(package)
            return package
        except IntegrityError:
            self.db.rollback()
            logger.warning(f"Package already exists: {package_name}")
            return self.find_by_name(package_name)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating package '{package_name}': {e}", exc_info=True)
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
