"""
Drop the packages table and let SQLAlchemy recreate it with the correct schema
"""
import psycopg2
from config import Config

DATABASE_URL = Config.DATABASE_URL

print("Dropping and recreating packages table...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Drop the table
    cursor.execute("DROP TABLE IF EXISTS packages CASCADE")
    conn.commit()
    print("✓ Dropped old table")

    cursor.close()
    conn.close()
    print("✓ Table will be recreated by Flask app on next startup")
    print("\nPlease restart your Flask app now.")

except Exception as e:
    print(f"✗ Error: {e}")
