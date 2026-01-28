"""
Database connection and session management
"""

import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool

from config import Config
from models.package import Base

logger = logging.getLogger(__name__)

# Global session factory
_session_factory = None


def init_database():
    """Initialize database engine and create tables"""
    global _session_factory

    try:
        engine = create_engine(
            Config.DATABASE_URL,
            poolclass=NullPool,  # Use NullPool for serverless/container environments
            echo=Config.SQLALCHEMY_ECHO,
            pool_pre_ping=True  # Verify connections before using
        )

        # Create tables if they don't exist
        Base.metadata.create_all(engine)

        # Create session factory
        _session_factory = scoped_session(
            sessionmaker(bind=engine, autocommit=False, autoflush=False)
        )

        logger.info("Database initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def get_session():
    """Get database session"""
    if _session_factory is None:
        init_database()
    return _session_factory()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    Automatically handles commit/rollback and cleanup

    Usage:
        with get_db_session() as session:
            # do database operations
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_database():
    """Close database connections"""
    global _session_factory
    if _session_factory:
        _session_factory.remove()
        logger.info("Database connections closed")
