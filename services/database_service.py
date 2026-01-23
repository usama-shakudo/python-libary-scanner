"""
PostgreSQL database service for package vulnerability management
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Service for interacting with PostgreSQL to manage package vulnerability data
    """

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        """
        Initialize database connection parameters

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.table_name = 'packages'
        logger.info(f"Database service initialized for {host}:{port}/{database}")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections

        Yields:
            psycopg2 connection object
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    def get_package_status(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get package status from database

        Args:
            package_name: Name of the package

        Returns:
            Package data dict with status, vulnerability_info, etc., or None if not found
        """
        try:
            logger.info(f"Checking package status in DB: {package_name}")

            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = f"""
                        SELECT * FROM {self.table_name}
                        WHERE package_name = %s
                    """
                    cursor.execute(query, (package_name,))
                    result = cursor.fetchone()

                    if result:
                        package_data = dict(result)
                        logger.info(f"Package found in DB: {package_name}, status: {package_data.get('status')}")
                        return package_data
                    else:
                        logger.info(f"Package not found in DB: {package_name}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching package status from DB: {str(e)}")
            return None

    def add_package_pending(self, package_name: str) -> bool:
        """
        Add a new package to the database with 'pending' status

        Args:
            package_name: Name of the package

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Adding package to DB with pending status: {package_name}")

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                        INSERT INTO {self.table_name}
                        (package_name, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (package_name) DO NOTHING
                    """
                    now = datetime.utcnow()
                    cursor.execute(query, (package_name, 'pending', now, now))

                    logger.info(f"Successfully added package to DB: {package_name}")
                    return True

        except Exception as e:
            logger.error(f"Error adding package to DB: {str(e)}")
            return False

    def is_package_vulnerable(self, package_data: Dict[str, Any]) -> bool:
        """
        Check if a package is vulnerable based on its status

        Args:
            package_data: Package data from database

        Returns:
            True if package is vulnerable, False otherwise
        """
        return package_data.get('status') == 'vulnerable'

    def get_vulnerability_info(self, package_data: Dict[str, Any]) -> str:
        """
        Get vulnerability information for a package

        Args:
            package_data: Package data from database

        Returns:
            Vulnerability information string
        """
        vuln_info = package_data.get('vulnerability_info', '')
        if vuln_info:
            return vuln_info
        return "This package has known security vulnerabilities. Contact your security team for details."

    def create_table_if_not_exists(self):
        """
        Create the packages table if it doesn't exist
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            package_name VARCHAR(255) PRIMARY KEY,
                            status VARCHAR(50) NOT NULL,
                            vulnerability_info TEXT,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                    """
                    cursor.execute(query)
                    logger.info(f"Table {self.table_name} created or already exists")
        except Exception as e:
            logger.error(f"Error creating table: {str(e)}")


# Singleton instance
_db_service: Optional[DatabaseService] = None


def init_database_service(host: str, port: int, database: str, user: str, password: str) -> DatabaseService:
    """
    Initialize the database service singleton

    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password

    Returns:
        DatabaseService instance
    """
    global _db_service
    _db_service = DatabaseService(host, port, database, user, password)

    # Create table if it doesn't exist
    _db_service.create_table_if_not_exists()

    logger.info("Database service initialized")
    return _db_service


def get_database_service() -> Optional[DatabaseService]:
    """
    Get the database service singleton instance

    Returns:
        DatabaseService instance or None if not initialized
    """
    return _db_service
