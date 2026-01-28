"""
Package model
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Package(Base):
    """Package vulnerability tracking model"""

    __tablename__ = 'packages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_name = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, default='pending')  # pending, safe, vulnerable, error
    vulnerability_info = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'package_name': self.package_name,
            'status': self.status,
            'vulnerability_info': self.vulnerability_info,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Package(name='{self.package_name}', status='{self.status}')>"
