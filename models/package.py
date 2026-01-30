"""
Package model
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class PackageStatus(str, Enum):
    """Package scan status enum"""
    # Working states
    PENDING = "pending"                    # Waiting for scan job to start
    DOWNLOADED = "downloaded"              # Downloaded from external PyPI

    # Final success states
    COMPLETED = "completed"                # Scanned, safe, uploaded to internal PyPI (ready to use)
    VULNERABLE = "vulnerable"              # Has vulnerabilities (blocked, not uploaded)

    # Failure states
    NOT_FOUND = "not_found"               # Package doesn't exist on external PyPI
    DOWNLOAD_ERROR = "download_error"     # Failed to download from external PyPI
    SCAN_ERROR = "scan_error"             # Download OK, but scan failed
    ERROR = "error"                        # Other/unknown error


class Package(Base):
    """Package vulnerability tracking model"""

    __tablename__ = 'packages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_name = Column(String(255), nullable=False, index=True)  # e.g., "numpy"
    version = Column(String(100), nullable=True)                    # e.g., "1.24.0" or "latest"
    python_version = Column(String(50), nullable=True)              # e.g., "3.11.0" (from pip User-Agent)
    status = Column(String(50), nullable=False, default=PackageStatus.PENDING.value)
    vulnerability_info = Column(JSON, nullable=True)
    error_message = Column(String(500), nullable=True)              # Error details for debugging
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Unique constraint: same package+version combination can only exist once
    __table_args__ = (
        {'sqlite_autoincrement': True}  # For SQLite compatibility
    )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'package_name': self.package_name,
            'version': self.version,
            'python_version': self.python_version,
            'status': self.status,
            'vulnerability_info': self.vulnerability_info,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        version_str = f"=={self.version}" if self.version else ""
        return f"<Package(name='{self.package_name}{version_str}', status='{self.status}')>"
