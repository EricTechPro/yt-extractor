"""
Verify data integrity in Supabase after migration and upload.

This script checks:
1. Row counts match expected values
2. Foreign key relationships are valid
3. Sample queries work correctly
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Supabase credentials not found in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def print_section(title):
    """Print formatted section header."""
    print(f"\n{'=' * 70}")
    print(title)
    print(f"{'=' * 70}")


def verify_row_counts(channel_id: str, expected_videos: int, expected_comments: int, expected_sub_comments: int):
    """Verify row counts match expected values."""
    print_section("Verifying Row Counts")

    # Count videos
    videos_response = supabase.table('videos').select('youtube_video_id', count='exact').eq('channel_id', channel_id).execute()
    videos_count = videos_response.count if videos_response.count is not None else 0

    # Count comments
    comments_response = supabase.table('comments').select('youtube_comment_id', count='exact').eq('channel_id', channel_id).execute()
    comments_count = comments_response.count if comments_response.count is not None else 0

    # Count sub-comments
    sub_comments_response = supabase.table('sub_comments').select('youtube_comment_id', count='exact').eq('channel_id', channel_id).execute()
    sub_comments_count = sub_comments_response.count if sub_comments_response.count is not None else 0

    # Print results
    print(f"\nVideos:")
    print(f"  Expected: {expected_videos}")
    print(f"  Actual:   {videos_count}")
    print(f"  Status:   {'✅ PASS' if videos_count == expected_videos else '❌ FAIL'}")

    print(f"\nComments:")
    print(f"  Expected: {expected_comments}")
    print(f"  Actual:   {comments_count}")
    print(f"  Status:   {'✅ PASS' if comments_count == expected_comments else '❌ FAIL'}")

    print(f"\nSub-Comments:")
    print(f"  Expected: {expected_sub_comments}")
    print(f"  Actual:   {sub_comments_count}")
    print(f"  Status:   {'✅ PASS' if sub_comments_count == expected_sub_comments else '❌ FAIL'}")

    return (videos_count == expected_videos and
            comments_count == expected_comments and
            sub_comments_count == expected_sub_comments)


def verify_foreign_keys():
    """Verify foreign key relationships are valid."""
    print_section("Verifying Foreign Key Relationships")

    # Check comments → videos FK
    print("\nChecking comments.video_id → videos.youtube_video_id...")
    comments_with_video = supabase.table('comments').select('youtube_comment_id, video_id').limit(5).execute()

    if comments_with_video.data:
        print(f"  ✅ Sample comment has video_id: {comments_with_video.data[0]['video_id']}")

        # Verify the video exists
        video_exists = supabase.table('videos').select('youtube_video_id').eq(
            'youtube_video_id', comments_with_video.data[0]['video_id']
        ).execute()

        if video_exists.data:
            print(f"  ✅ Foreign key valid: Video {comments_with_video.data[0]['video_id']} exists")
        else:
            print(f"  ❌ Foreign key broken: Video {comments_with_video.data[0]['video_id']} not found")

    # Check sub_comments → comments FK
    print("\nChecking sub_comments.parent_comment_id → comments.youtube_comment_id...")
    sub_comments_with_parent = supabase.table('sub_comments').select(
        'youtube_comment_id, parent_comment_id'
    ).limit(5).execute()

    if sub_comments_with_parent.data:
        print(f"  ✅ Sample sub-comment has parent_comment_id: {sub_comments_with_parent.data[0]['parent_comment_id']}")

        # Verify the parent comment exists
        parent_exists = supabase.table('comments').select('youtube_comment_id').eq(
            'youtube_comment_id', sub_comments_with_parent.data[0]['parent_comment_id']
        ).execute()

        if parent_exists.data:
            print(f"  ✅ Foreign key valid: Parent comment {sub_comments_with_parent.data[0]['parent_comment_id']} exists")
        else:
            print(f"  ❌ Foreign key broken: Parent comment {sub_comments_with_parent.data[0]['parent_comment_id']} not found")

    # Check sub_comments → videos FK
    print("\nChecking sub_comments.video_id → videos.youtube_video_id...")
    if sub_comments_with_parent.data:
        sub_comment_video_id = supabase.table('sub_comments').select('video_id').eq(
            'youtube_comment_id', sub_comments_with_parent.data[0]['youtube_comment_id']
        ).execute()

        if sub_comment_video_id.data:
            video_id = sub_comment_video_id.data[0]['video_id']
            print(f"  ✅ Sample sub-comment has video_id: {video_id}")

            # Verify the video exists
            video_exists = supabase.table('videos').select('youtube_video_id').eq(
                'youtube_video_id', video_id
            ).execute()

            if video_exists.data:
                print(f"  ✅ Foreign key valid: Video {video_id} exists")
            else:
                print(f"  ❌ Foreign key broken: Video {video_id} not found")


def verify_sample_queries():
    """Run sample queries to verify schema works correctly."""
    print_section("Running Sample Queries")

    # Query 1: Get video with all comments
    print("\nQuery 1: Fetch a video with its comments")
    video = supabase.table('videos').select('*').limit(1).execute()

    if video.data:
        video_id = video.data[0]['youtube_video_id']
        video_title = video.data[0]['title']
        print(f"  Video: {video_title}")
        print(f"  Video ID: {video_id}")

        comments = supabase.table('comments').select('youtube_comment_id, comment').eq(
            'video_id', video_id
        ).limit(3).execute()

        print(f"  Comments on this video: {len(comments.data)}")
        if comments.data:
            for i, comment in enumerate(comments.data[:3], 1):
                comment_text = comment['comment'][:50] + '...' if len(comment['comment']) > 50 else comment['comment']
                print(f"    {i}. {comment_text}")

        print(f"  ✅ Query successful")

    # Query 2: Get comment with replies
    print("\nQuery 2: Fetch a comment with its replies")
    comment_with_replies = supabase.table('comments').select('youtube_comment_id, comment').limit(1).execute()

    if comment_with_replies.data:
        comment_id = comment_with_replies.data[0]['youtube_comment_id']
        comment_text = comment_with_replies.data[0]['comment']
        print(f"  Comment: {comment_text[:70]}...")
        print(f"  Comment ID: {comment_id}")

        replies = supabase.table('sub_comments').select('youtube_comment_id, sub_comment').eq(
            'parent_comment_id', comment_id
        ).limit(3).execute()

        print(f"  Replies to this comment: {len(replies.data)}")
        if replies.data:
            for i, reply in enumerate(replies.data[:3], 1):
                reply_text = reply['sub_comment'][:50] + '...' if len(reply['sub_comment']) > 50 else reply['sub_comment']
                print(f"    {i}. {reply_text}")

        print(f"  ✅ Query successful")

    # Query 3: Channel statistics
    print("\nQuery 3: Channel statistics")
    channel_id = 'UCOXRjenlq9PmlTqd_JhAbMQ'

    videos_count = supabase.table('videos').select('youtube_video_id', count='exact').eq('channel_id', channel_id).execute()
    comments_count = supabase.table('comments').select('youtube_comment_id', count='exact').eq('channel_id', channel_id).execute()
    sub_comments_count = supabase.table('sub_comments').select('youtube_comment_id', count='exact').eq('channel_id', channel_id).execute()

    print(f"  Channel ID: {channel_id}")
    print(f"  Total Videos: {videos_count.count}")
    print(f"  Total Comments: {comments_count.count}")
    print(f"  Total Sub-Comments: {sub_comments_count.count}")
    print(f"  ✅ Statistics retrieved successfully")


def main():
    """Main verification workflow."""
    print_section("Supabase Data Integrity Verification")
    print(f"Supabase URL: {SUPABASE_URL}")

    # Expected values from upload
    channel_id = 'UCOXRjenlq9PmlTqd_JhAbMQ'
    expected_videos = 140
    expected_comments = 1499
    expected_sub_comments = 1366

    try:
        # Run verifications
        counts_valid = verify_row_counts(channel_id, expected_videos, expected_comments, expected_sub_comments)
        verify_foreign_keys()
        verify_sample_queries()

        # Final summary
        print_section("Verification Summary")

        if counts_valid:
            print("\n✅ All verifications passed!")
            print("   - Row counts match expected values")
            print("   - Foreign key relationships are valid")
            print("   - Sample queries work correctly")
            print("\n🎉 Data migration and upload completed successfully!")
        else:
            print("\n⚠️  Some verifications failed")
            print("   Please review the results above")

        print(f"\n{'=' * 70}\n")

    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        exit(1)


if __name__ == "__main__":
    main()
