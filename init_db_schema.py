#!/usr/bin/env python3
"""
Initialize database schema using SQLAlchemy
Run this inside the Kubernetes pod to create tables
"""

import sys
from sqlalchemy import create_engine, inspect
from config import Config
from models.package import Base

print("=" * 60)
print("DATABASE SCHEMA INITIALIZATION")
print("=" * 60)

# Mask password in URL for logging
db_url_masked = Config.SUPABASE_DATABASE_URL.split('@')[0].split(':')
db_url_masked = f"{db_url_masked[0]}:***@{Config.SUPABASE_DATABASE_URL.split('@')[1]}"
print(f"Database: {db_url_masked}")
print()

try:
    # Create engine
    engine = create_engine(Config.SUPABASE_DATABASE_URL, echo=True)

    print("Connecting to database...")
    conn = engine.connect()
    print("✓ Connection successful")

    # Check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"\nExisting tables: {existing_tables}")

    if 'packages' in existing_tables:
        print("\n⚠️  Table 'packages' already exists")

        # Show current schema
        columns = inspector.get_columns('packages')
        print("\nCurrent schema:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")

        print("\nTo recreate with correct schema, drop the table first:")
        print("  DROP TABLE packages CASCADE;")
        sys.exit(0)

    # Create all tables
    print("\nCreating tables...")
    Base.metadata.create_all(engine)

    # Verify table was created
    inspector = inspect(engine)
    if 'packages' in inspector.get_table_names():
        print("\n✓ Table 'packages' created successfully!")

        # Show new schema
        columns = inspector.get_columns('packages')
        print("\nTable schema:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")
    else:
        print("\n✗ Table creation failed!")
        sys.exit(1)

    conn.close()
    print("\n" + "=" * 60)
    print("✓ Database initialization complete")
    print("=" * 60)

except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
