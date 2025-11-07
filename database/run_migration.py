"""
Execute Database Migration for YouTube Comments Schema

This script executes the migration SQL to create the normalized schema
with videos, comments, and sub_comments tables in Supabase PostgreSQL.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_database_url():
    """
    Get PostgreSQL connection URL from Supabase URL.

    Returns:
        Database connection URL string
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_password = os.getenv("SUPABASE_DB_PASSWORD")

    if not supabase_url:
        print("❌ Error: SUPABASE_URL not found in .env file")
        print("   Please add your Supabase URL to .env")
        sys.exit(1)

    if not supabase_password:
        print("❌ Error: SUPABASE_DB_PASSWORD not found in .env file")
        print("   Please add your Supabase database password to .env")
        print()
        print("   You can find it at:")
        print("   https://app.supabase.com/ > Your Project > Settings > Database")
        print("   Look for 'Database Password' or 'Connection string'")
        sys.exit(1)

    # Extract project reference from Supabase URL
    # Format: https://xxxxx.supabase.co
    project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "")

    # Build PostgreSQL connection URL
    # Format: postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
    db_url = f"postgresql://postgres:{supabase_password}@db.{project_ref}.supabase.co:5432/postgres"

    return db_url


def execute_migration(migration_file):
    """
    Execute migration SQL file on Supabase PostgreSQL database.

    Args:
        migration_file: Path to SQL migration file

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'=' * 70}")
    print("Executing Database Migration")
    print(f"{'=' * 70}")
    print(f"Migration file: {migration_file}")

    # Check if migration file exists
    if not os.path.exists(migration_file):
        print(f"❌ Error: Migration file not found: {migration_file}")
        return False

    # Read migration SQL
    print("\n📄 Reading migration SQL...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    # Get database connection URL
    print("🔗 Connecting to Supabase PostgreSQL...")
    db_url = get_database_url()

    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        conn.autocommit = True  # Auto-commit each statement
        cursor = conn.cursor()

        print("✅ Connected successfully!")

        # Execute migration SQL
        print("\n⚠️  WARNING: This will DROP existing comments and sub_comments tables!")
        print("   All existing data will be LOST.")
        print()

        confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Migration cancelled by user")
            cursor.close()
            conn.close()
            return False

        print("\n🔄 Executing migration SQL...")

        # Execute the entire SQL script
        cursor.execute(migration_sql)

        print("✅ Migration SQL executed successfully!")

        # Verify tables were created
        print("\n🔍 Verifying tables...")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('videos', 'comments', 'sub_comments')
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()

        if len(tables) == 3:
            print("✅ All 3 tables created successfully:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print(f"⚠️  Warning: Expected 3 tables, found {len(tables)}:")
            for table in tables:
                print(f"   - {table[0]}")

        # Verify indexes were created
        print("\n🔍 Verifying indexes...")
        cursor.execute("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE tablename IN ('videos', 'comments', 'sub_comments')
            AND schemaname = 'public'
            ORDER BY tablename, indexname;
        """)

        indexes = cursor.fetchall()
        print(f"✅ Found {len(indexes)} indexes:")
        for idx_name, tbl_name in indexes:
            print(f"   - {tbl_name}.{idx_name}")

        # Close connection
        cursor.close()
        conn.close()

        print(f"\n{'=' * 70}")
        print("✅ Migration completed successfully!")
        print(f"{'=' * 70}\n")

        return True

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Main entry point."""
    migration_file = "migrations/001_normalized_schema.sql"

    success = execute_migration(migration_file)

    if success:
        print("✅ Migration successful! You can now upload data with:")
        print("   python3 database/upload_to_supabase.py --channel-id UCOXRjenlq9PmlTqd_JhAbMQ")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
