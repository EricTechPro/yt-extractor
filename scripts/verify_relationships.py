#!/usr/bin/env python3
"""
Verify foreign key relationships between comments and sub_comments tables.
Tests that youtube_comment_id properly links parent comments to their replies.
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

print("=" * 70)
print("🔍 Verifying Foreign Key Relationships")
print("=" * 70)

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Test 1: Check that youtube_comment_id is populated
    print("\n📊 Test 1: YouTube Comment ID Population")
    print("-" * 70)

    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(youtube_comment_id) as with_id,
               COUNT(*) - COUNT(youtube_comment_id) as missing_id
        FROM comments
        WHERE channel_id = %s
    """, (CHANNEL_ID,))

    total, with_id, missing_id = cursor.fetchone()
    print(f"   Total comments: {total}")
    print(f"   With YouTube ID: {with_id}")
    print(f"   Missing YouTube ID: {missing_id}")

    if missing_id == 0:
        print(f"   ✅ All comments have YouTube IDs!")
    else:
        print(f"   ⚠️  Warning: {missing_id} comments missing YouTube IDs")

    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(youtube_comment_id) as with_id,
               COUNT(*) - COUNT(youtube_comment_id) as missing_id
        FROM sub_comments
        WHERE channel_id = %s
    """, (CHANNEL_ID,))

    total, with_id, missing_id = cursor.fetchone()
    print(f"\n   Total sub-comments: {total}")
    print(f"   With YouTube ID: {with_id}")
    print(f"   Missing YouTube ID: {missing_id}")

    if missing_id == 0:
        print(f"   ✅ All sub-comments have YouTube IDs!")
    else:
        print(f"   ⚠️  Warning: {missing_id} sub-comments missing YouTube IDs")

    # Test 2: Check parent-child relationships
    print("\n📊 Test 2: Parent-Child Relationship Validation")
    print("-" * 70)

    cursor.execute("""
        SELECT
            COUNT(*) as total_replies,
            COUNT(DISTINCT sc.parentcommentid) as unique_parents,
            COUNT(DISTINCT c.youtube_comment_id) as matched_parents
        FROM sub_comments sc
        LEFT JOIN comments c ON sc.parentcommentid = c.youtube_comment_id
        WHERE sc.channel_id = %s
    """, (CHANNEL_ID,))

    total_replies, unique_parents, matched_parents = cursor.fetchone()
    print(f"   Total replies: {total_replies}")
    print(f"   Unique parent IDs referenced: {unique_parents}")
    print(f"   Matched parent comments: {matched_parents}")

    if unique_parents == matched_parents:
        print(f"   ✅ All parent references match existing comments!")
    else:
        print(f"   ⚠️  Warning: {unique_parents - matched_parents} orphaned parent references")

    # Test 3: Sample JOIN query to show relationships
    print("\n📊 Test 3: Sample Parent-Child Data")
    print("-" * 70)

    cursor.execute("""
        SELECT
            c.comment as parent_comment,
            c.videotitle,
            c.likescount as parent_likes,
            COUNT(sc.id) as reply_count,
            SUM(sc.likecount) as total_reply_likes
        FROM comments c
        LEFT JOIN sub_comments sc ON c.youtube_comment_id = sc.parentcommentid
        WHERE c.channel_id = %s
        GROUP BY c.id, c.comment, c.videotitle, c.likescount
        HAVING COUNT(sc.id) > 0
        ORDER BY reply_count DESC
        LIMIT 5
    """, (CHANNEL_ID,))

    results = cursor.fetchall()

    if results:
        print(f"\n   Top 5 comments with most replies:")
        for i, (comment, video, parent_likes, reply_count, total_reply_likes) in enumerate(results, 1):
            comment_preview = comment[:60] + "..." if len(comment) > 60 else comment
            print(f"\n   {i}. {comment_preview}")
            print(f"      Video: {video}")
            print(f"      Parent likes: {parent_likes} | Replies: {reply_count} | Reply likes: {total_reply_likes or 0}")
    else:
        print("   ⚠️  No comments with replies found")

    # Test 4: Check for orphaned replies
    print("\n📊 Test 4: Orphaned Replies Check")
    print("-" * 70)

    cursor.execute("""
        SELECT COUNT(*) as orphaned_count
        FROM sub_comments sc
        LEFT JOIN comments c ON sc.parentcommentid = c.youtube_comment_id
        WHERE sc.channel_id = %s AND c.id IS NULL
    """, (CHANNEL_ID,))

    orphaned_count = cursor.fetchone()[0]

    if orphaned_count == 0:
        print(f"   ✅ No orphaned replies found!")
    else:
        print(f"   ⚠️  Found {orphaned_count} orphaned replies (no matching parent)")

        # Show sample orphaned replies
        cursor.execute("""
            SELECT sc.subcomment, sc.parentcommentid, sc.videotitle
            FROM sub_comments sc
            LEFT JOIN comments c ON sc.parentcommentid = c.youtube_comment_id
            WHERE sc.channel_id = %s AND c.id IS NULL
            LIMIT 3
        """, (CHANNEL_ID,))

        orphaned = cursor.fetchall()
        print(f"\n   Sample orphaned replies:")
        for comment, parent_id, video in orphaned:
            comment_preview = comment[:50] + "..." if len(comment) > 50 else comment
            print(f"      - {comment_preview}")
            print(f"        Parent ID: {parent_id}")
            print(f"        Video: {video}")

    # Test 5: Statistics
    print("\n📊 Test 5: Overall Statistics")
    print("-" * 70)

    cursor.execute("""
        SELECT
            COUNT(DISTINCT c.id) as total_comments,
            COUNT(DISTINCT sc.id) as total_replies,
            COUNT(DISTINCT c.id) FILTER (WHERE EXISTS (
                SELECT 1 FROM sub_comments sc2
                WHERE sc2.parentcommentid = c.youtube_comment_id
            )) as comments_with_replies,
            ROUND(AVG(reply_counts.count), 2) as avg_replies_per_parent
        FROM comments c
        LEFT JOIN sub_comments sc ON c.youtube_comment_id = sc.parentcommentid
        LEFT JOIN (
            SELECT parentcommentid, COUNT(*) as count
            FROM sub_comments
            WHERE channel_id = %s
            GROUP BY parentcommentid
        ) reply_counts ON c.youtube_comment_id = reply_counts.parentcommentid
        WHERE c.channel_id = %s
    """, (CHANNEL_ID, CHANNEL_ID))

    total_comments, total_replies, comments_with_replies, avg_replies = cursor.fetchone()

    print(f"   Total comments: {total_comments}")
    print(f"   Total replies: {total_replies}")
    print(f"   Comments with replies: {comments_with_replies}")
    print(f"   Average replies per parent: {avg_replies or 0}")

    if comments_with_replies > 0:
        coverage = (comments_with_replies / total_comments) * 100
        print(f"   Coverage: {coverage:.1f}% of comments have replies")

    print("\n" + "=" * 70)
    print("✅ Relationship Verification Complete!")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ Error verifying relationships: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
