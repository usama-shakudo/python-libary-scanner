"""
Quick script to check database connection and view packages table
Run with: python3 check_db.py
"""

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not installed")
    print("Install with: pip3 install psycopg2-binary")
    exit(1)

from config import Config

# Load database URL from environment variables via Config
DATABASE_URL = Config.SUPABASE_DATABASE_URL

if not DATABASE_URL:
    print("ERROR: SUPABASE_DATABASE_URL not configured")
    print("Make sure .env file exists with SUPABASE_DATABASE_URL set")
    exit(1)

print("=" * 60)
print("DATABASE CONNECTION TEST")
print("=" * 60)
# Don't print full URL to avoid exposing credentials
print(f"Connection: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}\n")

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    print("✓ Database connection successful")

    # Check if table exists
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'packages'
        )
    """)
    exists = cursor.fetchone()[0]

    if exists:
        print("✓ Table 'packages' exists")
    else:
        print("✗ Table 'packages' does NOT exist")
        print("\nTable should be created by Flask app on startup.")
        print("Please start your Flask app (python3 app.py) to create the table.")
        cursor.close()
        conn.close()
        exit(0)

    # Query all packages
    print("\n" + "=" * 60)
    print("PACKAGES IN DATABASE")
    print("=" * 60)

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM packages ORDER BY created_at DESC")
    packages = cursor.fetchall()

    if packages:
        print(f"\nFound {len(packages)} package(s):\n")
        for pkg in packages:
            print(f"Package: {pkg['package_name']}")
            print(f"  Status: {pkg['status']}")
            print(f"  Created: {pkg['created_at']}")
            print(f"  Updated: {pkg['updated_at']}")
            if pkg.get('vulnerability_info'):
                print(f"  Vuln Info: {pkg['vulnerability_info']}")
            print()
    else:
        print("\nNo packages found in database")

    cursor.close()
    conn.close()

    print("=" * 60)
    print("✓ Database check complete")
    print("=" * 60)

except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    print("\nMake sure SUPABASE_DATABASE_URL is configured in your .env file:")
    print("SUPABASE_DATABASE_URL=postgresql://user:password@host:5432/database")
