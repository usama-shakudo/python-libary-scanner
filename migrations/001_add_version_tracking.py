"""
Migration: Add version tracking columns to packages table

Adds:
- version: Package version (e.g., "1.24.0" or "latest")
- python_version: Python version from pip User-Agent (e.g., "3.11.0")
- error_message: Error details for failed scans

Usage:
    python migrations/001_add_version_tracking.py
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import get_engine, get_session
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def run_migration():
    """Run the migration to add version tracking columns"""
    try:
        engine = get_engine()

        with engine.connect() as conn:
            logger.info("Starting migration: Add version tracking columns")

            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'packages'
                AND column_name IN ('version', 'python_version', 'error_message')
            """))

            existing_columns = {row[0] for row in result}

            # Add version column
            if 'version' not in existing_columns:
                logger.info("Adding 'version' column...")
                conn.execute(text("""
                    ALTER TABLE packages
                    ADD COLUMN version VARCHAR(100)
                """))
                logger.info("✓ Added 'version' column")
            else:
                logger.info("✓ Column 'version' already exists")

            # Add python_version column
            if 'python_version' not in existing_columns:
                logger.info("Adding 'python_version' column...")
                conn.execute(text("""
                    ALTER TABLE packages
                    ADD COLUMN python_version VARCHAR(50)
                """))
                logger.info("✓ Added 'python_version' column")
            else:
                logger.info("✓ Column 'python_version' already exists")

            # Add error_message column
            if 'error_message' not in existing_columns:
                logger.info("Adding 'error_message' column...")
                conn.execute(text("""
                    ALTER TABLE packages
                    ADD COLUMN error_message VARCHAR(500)
                """))
                logger.info("✓ Added 'error_message' column")
            else:
                logger.info("✓ Column 'error_message' already exists")

            # Update existing records to have version = 'latest' where NULL
            logger.info("Updating existing records to set version='latest' where NULL...")
            result = conn.execute(text("""
                UPDATE packages
                SET version = 'latest'
                WHERE version IS NULL
            """))
            logger.info(f"✓ Updated {result.rowcount} records")

            # Commit changes
            conn.commit()

            logger.info("Migration completed successfully!")
            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


def rollback_migration():
    """Rollback the migration (remove added columns)"""
    try:
        engine = get_engine()

        with engine.connect() as conn:
            logger.info("Starting rollback: Remove version tracking columns")

            # Check which columns exist
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'packages'
                AND column_name IN ('version', 'python_version', 'error_message')
            """))

            existing_columns = {row[0] for row in result}

            # Remove version column
            if 'version' in existing_columns:
                logger.info("Removing 'version' column...")
                conn.execute(text("ALTER TABLE packages DROP COLUMN version"))
                logger.info("✓ Removed 'version' column")

            # Remove python_version column
            if 'python_version' in existing_columns:
                logger.info("Removing 'python_version' column...")
                conn.execute(text("ALTER TABLE packages DROP COLUMN python_version"))
                logger.info("✓ Removed 'python_version' column")

            # Remove error_message column
            if 'error_message' in existing_columns:
                logger.info("Removing 'error_message' column...")
                conn.execute(text("ALTER TABLE packages DROP COLUMN error_message"))
                logger.info("✓ Removed 'error_message' column")

            # Commit changes
            conn.commit()

            logger.info("Rollback completed successfully!")
            return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Database migration for version tracking')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    if args.rollback:
        success = rollback_migration()
    else:
        success = run_migration()

    sys.exit(0 if success else 1)
