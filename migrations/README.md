# Database Migrations

This folder contains database migration scripts for the Python Library Scanner.

## Running Migrations

### Apply Migration

To apply a migration:

```bash
python migrations/001_add_version_tracking.py
```

### Rollback Migration

To rollback a migration:

```bash
python migrations/001_add_version_tracking.py --rollback
```

## Migration 001: Add Version Tracking

**File**: `001_add_version_tracking.py`

**Purpose**: Adds version tracking capabilities to the packages table.

**Changes**:
- Adds `version` column (VARCHAR(100)) - stores package version like "1.24.0" or "latest"
- Adds `python_version` column (VARCHAR(50)) - stores Python version from pip User-Agent like "3.11.0"
- Adds `error_message` column (VARCHAR(500)) - stores error details for failed scans

**Safety**:
- Checks if columns already exist before adding
- Updates existing records to set version='latest' where NULL
- Supports rollback with `--rollback` flag

**Required Before Running**:
- Ensure `SUPABASE_DATABASE_URL` is set in `.env` file
- Database connection must be available

## Notes

- Migrations are numbered sequentially (001, 002, etc.)
- Always backup your database before running migrations
- Migrations should be idempotent (safe to run multiple times)
