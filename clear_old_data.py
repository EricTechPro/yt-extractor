#!/usr/bin/env python3
"""
Temporary script to clear old database records before re-uploading with YouTube IDs.
This removes records that don't have youtube_comment_id populated.
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
CHANNEL_ID = 'UCOXRjenlq9PmlTqd_JhAbMQ'

if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not found in .env file")
    exit(1)

print(f"🗑️  Clearing old records for channel: {CHANNEL_ID}")
print("=" * 60)

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Count existing records
    cursor.execute("SELECT COUNT(*) FROM comments WHERE channel_id = %s", (CHANNEL_ID,))
    comment_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sub_comments WHERE channel_id = %s", (CHANNEL_ID,))
    sub_comment_count = cursor.fetchone()[0]

    print(f"\n📊 Current records in database:")
    print(f"   Comments: {comment_count}")
    print(f"   Sub-comments: {sub_comment_count}")

    # Delete sub_comments first (due to FK constraint)
    print(f"\n🗑️  Deleting sub_comments...")
    cursor.execute("DELETE FROM sub_comments WHERE channel_id = %s", (CHANNEL_ID,))
    deleted_subs = cursor.rowcount
    print(f"   ✅ Deleted {deleted_subs} sub-comments")

    # Delete comments
    print(f"\n🗑️  Deleting comments...")
    cursor.execute("DELETE FROM comments WHERE channel_id = %s", (CHANNEL_ID,))
    deleted_comments = cursor.rowcount
    print(f"   ✅ Deleted {deleted_comments} comments")

    # Commit transaction
    conn.commit()

    print(f"\n✅ Database cleared successfully!")
    print(f"   Total records deleted: {deleted_comments + deleted_subs}")

except Exception as e:
    print(f"\n❌ Error clearing database: {e}")
    if conn:
        conn.rollback()
    exit(1)

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()

print("\n" + "=" * 60)
print("✅ Ready for re-upload with YouTube comment IDs")
