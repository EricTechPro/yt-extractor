"""
Supabase Upload Script for YouTube Comments

This script uploads extracted YouTube comments and replies from JSON files
to Supabase database tables. It supports batch insertion, duplicate detection,
and resumable operations.
"""

# ============================================================================
# IMPORTS
# ============================================================================

import json
import os
import argparse
import re
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Load environment variables from .env file
load_dotenv()


# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    'output_dir': 'output',              # Directory containing JSON files
    'batch_size': 100,                   # Records per batch insert
    'retry_attempts': 3,                 # Number of retry attempts for failures
}


# ============================================================================
# SUPABASE CLIENT INITIALIZATION
# ============================================================================

# Load Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validate Supabase credentials are present
if not SUPABASE_URL or not SUPABASE_KEY:
    print("=" * 70)
    print("ERROR: Supabase credentials not found or not configured properly")
    print("=" * 70)
    print()
    print("Please follow these steps:")
    print("1. Copy .env.example to .env (if not already done)")
    print("   $ cp .env.example .env")
    print()
    print("2. Get your Supabase credentials from:")
    print("   https://app.supabase.com/ > Your Project > Settings > API")
    print()
    print("3. Edit .env and add your credentials:")
    print("   SUPABASE_URL=https://your-project-ref.supabase.co")
    print("   SUPABASE_KEY=your_service_role_key_or_anon_key")
    print()
    print("=" * 70)
    exit(1)

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    print("Please verify your SUPABASE_URL and SUPABASE_KEY are correct")
    raise


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_channel_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract channel ID from JSON filename.

    Expected formats:
    - [CHANNEL_ID]_comments.json
    - [CHANNEL_ID]_sub_comments.json

    Args:
        filename: Name of the JSON file

    Returns:
        Channel ID or None if pattern doesn't match
    """
    pattern = r"^(.+?)_(?:sub_)?comments\.json$"
    match = re.match(pattern, filename)
    if match:
        return match.group(1)
    return None


def load_json_file(file_path: str) -> List[Dict]:
    """
    Load and parse JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        List of dictionaries from JSON file

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"Warning: {file_path} does not contain a JSON array")
                return []
            return data
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        raise


def find_channel_files(output_dir: str) -> Dict[str, Dict[str, str]]:
    """
    Find all channel JSON files in output directory.

    Args:
        output_dir: Directory containing JSON files

    Returns:
        Dictionary mapping channel_id to dict with 'videos', 'comments', and 'sub_comments' file paths
        Example: {
            'UCxxxxxx': {
                'videos': 'output/UCxxxxxx_videos.json',
                'comments': 'output/UCxxxxxx_comments.json',
                'sub_comments': 'output/UCxxxxxx_sub_comments.json'
            }
        }
    """
    channels = {}

    if not os.path.exists(output_dir):
        print(f"Error: Output directory '{output_dir}' does not exist")
        return channels

    for filename in os.listdir(output_dir):
        if not filename.endswith('.json'):
            continue

        # Extract channel ID from filename pattern
        # Patterns: [CHANNEL_ID]_videos.json, [CHANNEL_ID]_comments.json, [CHANNEL_ID]_sub_comments.json
        pattern = r"^(.+?)_(?:videos|sub_comments|comments)\.json$"
        match = re.match(pattern, filename)
        if not match:
            continue

        channel_id = match.group(1)

        if channel_id not in channels:
            channels[channel_id] = {'videos': None, 'comments': None, 'sub_comments': None}

        file_path = os.path.join(output_dir, filename)

        if filename.endswith('_videos.json'):
            channels[channel_id]['videos'] = file_path
        elif filename.endswith('_sub_comments.json'):
            channels[channel_id]['sub_comments'] = file_path
        elif filename.endswith('_comments.json'):
            channels[channel_id]['comments'] = file_path

    return channels


def prepare_video_record(video: Dict, channel_id: str) -> Dict:
    """
    Prepare a video record for database insertion.

    Maps JSON fields to database columns (normalized schema).
    Note: PostgreSQL converts unquoted column names to lowercase,
    so we use lowercase keys for Supabase PostgREST API.

    Args:
        video: Video dictionary from JSON
        channel_id: YouTube channel ID

    Returns:
        Dictionary ready for database insertion
    """
    return {
        'youtube_video_id': video.get('youtubeVideoId'),
        'channel_id': channel_id,
        'title': video.get('title'),
        'description': video.get('description'),
        'tags': video.get('tags', []),
        'published_at': video.get('publishedAt'),
        'channel_title': video.get('channelTitle'),
        'duration': video.get('duration'),
        'view_count': video.get('viewCount', 0),
    }


def prepare_comment_record(comment: Dict, channel_id: str) -> Dict:
    """
    Prepare a comment record for database insertion.

    Maps JSON fields to database columns (normalized schema).
    Note: PostgreSQL converts unquoted column names to lowercase,
    so we use lowercase keys for Supabase PostgREST API.

    Args:
        comment: Comment dictionary from JSON
        channel_id: YouTube channel ID

    Returns:
        Dictionary ready for database insertion
    """
    return {
        'youtube_comment_id': comment.get('youtubeCommentId'),
        'video_id': comment.get('videoId'),
        'channel_id': channel_id,
        'comment': comment.get('comment'),
        'date_post_comment': comment.get('datePostComment'),
        'likes_count': comment.get('likesCount', 0),
    }


def prepare_sub_comment_record(sub_comment: Dict, channel_id: str) -> Dict:
    """
    Prepare a sub-comment (reply) record for database insertion.

    Maps JSON fields to database columns (normalized schema).
    Note: PostgreSQL converts unquoted column names to lowercase,
    so we use lowercase keys for Supabase PostgREST API.

    Args:
        sub_comment: Sub-comment dictionary from JSON
        channel_id: YouTube channel ID

    Returns:
        Dictionary ready for database insertion
    """
    return {
        'youtube_comment_id': sub_comment.get('youtubeCommentId'),
        'video_id': sub_comment.get('videoId'),
        'parent_comment_id': sub_comment.get('parentCommentId'),
        'channel_id': channel_id,
        'sub_comment': sub_comment.get('subComment'),
        'date_post_sub_comment': sub_comment.get('datePostSubComment'),
        'like_count': sub_comment.get('likeCount', 0),
    }


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def batch_insert_records(
    table_name: str,
    records: List[Dict],
    batch_size: int,
    description: str = "Uploading records"
) -> Tuple[int, int, List[str]]:
    """
    Insert records into Supabase table in batches.

    Args:
        table_name: Name of the database table
        records: List of record dictionaries to insert
        batch_size: Number of records per batch
        description: Description for progress bar

    Returns:
        Tuple of (successful_count, failed_count, error_messages)
    """
    successful = 0
    failed = 0
    errors = []

    # Process in batches
    total_batches = (len(records) + batch_size - 1) // batch_size

    with tqdm(total=len(records), desc=description, unit="records") as pbar:
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            try:
                # Insert batch into Supabase
                response = supabase.table(table_name).insert(batch).execute()

                # Check if insertion was successful
                if response.data:
                    successful += len(batch)
                else:
                    failed += len(batch)
                    error_msg = f"Batch {i//batch_size + 1}: No data returned from insert"
                    errors.append(error_msg)

            except Exception as e:
                failed += len(batch)
                error_msg = f"Batch {i//batch_size + 1}: {str(e)}"
                errors.append(error_msg)
                print(f"\n⚠️  Error inserting batch: {e}")

            pbar.update(len(batch))

    return successful, failed, errors


def run_migration(migration_file: str) -> bool:
    """
    Run database migration from SQL file.

    Args:
        migration_file: Path to migration SQL file

    Returns:
        True if migration successful, False otherwise
    """
    try:
        print(f"\n{'=' * 70}")
        print("Running Database Migration")
        print(f"{'=' * 70}")
        print(f"Migration file: {migration_file}")

        if not os.path.exists(migration_file):
            print(f"❌ Migration file not found: {migration_file}")
            return False

        # Read migration SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()

        print("\n⚠️  WARNING: This migration will DROP existing tables!")
        print("   - sub_comments table will be DROPPED")
        print("   - comments table will be DROPPED")
        print("   - All existing data will be LOST")
        print()

        confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Migration cancelled by user")
            return False

        print("\n🔄 Executing migration...")

        # Execute migration SQL
        # Note: Supabase Python client doesn't have a direct SQL execution method for the service role
        # We'll use the rpc method to execute raw SQL
        try:
            # Split SQL into individual statements (simple split by semicolon)
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

            for i, statement in enumerate(statements, 1):
                if statement:
                    # Skip comments and empty statements
                    if statement.startswith('--') or not statement.strip():
                        continue

                    print(f"   Executing statement {i}/{len(statements)}...")
                    supabase.rpc('exec_sql', {'query': statement}).execute()

            print("\n✅ Migration completed successfully!")
            print(f"{'=' * 70}\n")
            return True

        except Exception as e:
            # If rpc doesn't work, inform user to run SQL manually
            print(f"\n⚠️  Automatic migration via Python client not supported.")
            print(f"   Please run the migration manually in Supabase SQL Editor:")
            print(f"\n   1. Go to https://app.supabase.com/")
            print(f"   2. Select your project")
            print(f"   3. Go to SQL Editor")
            print(f"   4. Paste the contents of: {migration_file}")
            print(f"   5. Execute the SQL")
            print()

            proceed = input("Have you run the migration manually? (yes/no): ").strip().lower()
            if proceed == 'yes':
                print("✅ Migration confirmed!")
                return True
            else:
                print("❌ Please run the migration before uploading data")
                return False

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def check_existing_records(table_name: str, channel_id: str) -> int:
    """
    Check how many records already exist for a channel.

    Args:
        table_name: Name of the database table
        channel_id: YouTube channel ID

    Returns:
        Count of existing records
    """
    try:
        # Use count query with the new schema (no 'id' column, use PKs instead)
        if table_name == 'videos':
            pk_column = "youtube_video_id"
        else:
            pk_column = "youtube_comment_id"

        response = supabase.table(table_name).select(
            pk_column, count="exact"
        ).eq("channel_id", channel_id).execute()

        return response.count if response.count is not None else 0
    except Exception as e:
        print(f"Warning: Could not check existing records: {e}")
        return 0


def upload_channel_data(
    channel_id: str,
    videos_file: Optional[str],
    comments_file: Optional[str],
    sub_comments_file: Optional[str],
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Upload videos, comments, and sub-comments for a single channel.

    IMPORTANT: Upload order matters due to foreign key constraints:
    1. Videos (parent table)
    2. Comments (references videos)
    3. Sub-comments (references both videos and comments)

    Args:
        channel_id: YouTube channel ID
        videos_file: Path to videos JSON file (or None)
        comments_file: Path to comments JSON file (or None)
        sub_comments_file: Path to sub-comments JSON file (or None)
        dry_run: If True, validate but don't insert data

    Returns:
        Dictionary with upload statistics
    """
    stats = {
        'videos_uploaded': 0,
        'videos_failed': 0,
        'comments_uploaded': 0,
        'comments_failed': 0,
        'sub_comments_uploaded': 0,
        'sub_comments_failed': 0,
        'videos_existing': 0,
        'comments_existing': 0,
        'sub_comments_existing': 0,
    }

    print(f"\n{'=' * 70}")
    print(f"Processing Channel: {channel_id}")
    print(f"{'=' * 70}")

    # Step 1: Upload videos (parent table - must be first)
    if videos_file and os.path.exists(videos_file):
        print(f"\n📄 Loading videos from: {videos_file}")
        videos_data = load_json_file(videos_file)

        if videos_data:
            print(f"   Found {len(videos_data)} videos")

            # Check existing records
            existing_count = check_existing_records('videos', channel_id)
            stats['videos_existing'] = existing_count

            if existing_count > 0:
                print(f"   ⚠️  Warning: {existing_count} video records already exist for this channel")

            if not dry_run:
                # Prepare records
                prepared_videos = [
                    prepare_video_record(video, channel_id)
                    for video in videos_data
                ]

                # Insert in batches
                successful, failed, errors = batch_insert_records(
                    'videos',
                    prepared_videos,
                    CONFIG['batch_size'],
                    f"Uploading videos for {channel_id}"
                )

                stats['videos_uploaded'] = successful
                stats['videos_failed'] = failed

                print(f"\n   ✅ Uploaded: {successful} videos")
                if failed > 0:
                    print(f"   ❌ Failed: {failed} videos")
            else:
                print(f"   🔍 DRY RUN: Would upload {len(videos_data)} videos")
        else:
            print(f"   ⚠️  No videos found in file")
    else:
        print(f"\n   ⏭️  No videos file found")

    # Step 2: Upload top-level comments (requires videos to exist)

    # Upload top-level comments
    if comments_file and os.path.exists(comments_file):
        print(f"\n📄 Loading comments from: {comments_file}")
        comments_data = load_json_file(comments_file)

        if comments_data:
            print(f"   Found {len(comments_data)} comments")

            # Check existing records
            existing_count = check_existing_records('comments', channel_id)
            stats['comments_existing'] = existing_count

            if existing_count > 0:
                print(f"   ⚠️  Warning: {existing_count} records already exist for this channel")
                print(f"   This may result in duplicate records if data hasn't changed")

            if not dry_run:
                # Prepare records
                prepared_comments = [
                    prepare_comment_record(comment, channel_id)
                    for comment in comments_data
                ]

                # Insert in batches
                successful, failed, errors = batch_insert_records(
                    'comments',
                    prepared_comments,
                    CONFIG['batch_size'],
                    f"Uploading comments for {channel_id}"
                )

                stats['comments_uploaded'] = successful
                stats['comments_failed'] = failed

                print(f"\n   ✅ Uploaded: {successful} comments")
                if failed > 0:
                    print(f"   ❌ Failed: {failed} comments")
            else:
                print(f"   🔍 DRY RUN: Would upload {len(comments_data)} comments")
        else:
            print(f"   ⚠️  No comments found in file")
    else:
        print(f"\n   ⏭️  No comments file found")

    # Upload sub-comments (replies)
    if sub_comments_file and os.path.exists(sub_comments_file):
        print(f"\n📄 Loading sub-comments from: {sub_comments_file}")
        sub_comments_data = load_json_file(sub_comments_file)

        if sub_comments_data:
            print(f"   Found {len(sub_comments_data)} sub-comments")

            # Check existing records
            existing_count = check_existing_records('sub_comments', channel_id)
            stats['sub_comments_existing'] = existing_count

            if existing_count > 0:
                print(f"   ⚠️  Warning: {existing_count} records already exist for this channel")
                print(f"   This may result in duplicate records if data hasn't changed")

            if not dry_run:
                # Prepare records
                prepared_sub_comments = [
                    prepare_sub_comment_record(sub_comment, channel_id)
                    for sub_comment in sub_comments_data
                ]

                # Insert in batches
                successful, failed, errors = batch_insert_records(
                    'sub_comments',
                    prepared_sub_comments,
                    CONFIG['batch_size'],
                    f"Uploading sub-comments for {channel_id}"
                )

                stats['sub_comments_uploaded'] = successful
                stats['sub_comments_failed'] = failed

                print(f"\n   ✅ Uploaded: {successful} sub-comments")
                if failed > 0:
                    print(f"   ❌ Failed: {failed} sub-comments")
            else:
                print(f"   🔍 DRY RUN: Would upload {len(sub_comments_data)} sub-comments")
        else:
            print(f"   ⚠️  No sub-comments found in file")
    else:
        print(f"\n   ⏭️  No sub-comments file found")

    return stats


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point for the upload script."""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Upload YouTube comment data from JSON files to Supabase database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload specific channel
  python upload_to_supabase.py --channel-id UCxxxxxx

  # Upload all channels in output directory
  python upload_to_supabase.py --all

  # Dry run (validate without inserting)
  python upload_to_supabase.py --channel-id UCxxxxxx --dry-run

  # Custom batch size
  python upload_to_supabase.py --all --batch-size 50
        """
    )

    parser.add_argument(
        '--channel-id',
        type=str,
        help='YouTube channel ID to upload (e.g., UCxxxxxx)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Upload all channels found in output directory'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate files without inserting data into database'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=CONFIG['batch_size'],
        help=f'Number of records per batch (default: {CONFIG["batch_size"]})'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=CONFIG['output_dir'],
        help=f'Directory containing JSON files (default: {CONFIG["output_dir"]})'
    )

    parser.add_argument(
        '--run-migration',
        action='store_true',
        help='Run database migration before uploading data'
    )

    parser.add_argument(
        '--migration-file',
        type=str,
        default='database/migrations/001_normalized_schema.sql',
        help='Path to migration SQL file (default: database/migrations/001_normalized_schema.sql)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.channel_id and not args.all:
        parser.error("Please specify either --channel-id or --all")

    if args.channel_id and args.all:
        parser.error("Cannot specify both --channel-id and --all")

    # Update config with command-line arguments
    CONFIG['batch_size'] = args.batch_size
    CONFIG['output_dir'] = args.output_dir

    # Print header
    print("\n" + "=" * 70)
    print("YouTube Comments → Supabase Upload Script (Normalized Schema)")
    print("=" * 70)
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Output Directory: {CONFIG['output_dir']}")
    print(f"Batch Size: {CONFIG['batch_size']}")
    if args.dry_run:
        print("Mode: DRY RUN (no data will be inserted)")
    print("=" * 70)

    # Run migration if requested
    if args.run_migration and not args.dry_run:
        migration_success = run_migration(args.migration_file)
        if not migration_success:
            print("\n❌ Migration failed or was cancelled. Aborting upload.")
            return

    # Find channel files
    all_channels = find_channel_files(CONFIG['output_dir'])

    if not all_channels:
        print(f"\n❌ No channel JSON files found in '{CONFIG['output_dir']}'")
        print("   Make sure you've run src/main.py to extract comments first")
        return

    print(f"\nFound {len(all_channels)} channel(s) with data:")
    for channel_id in all_channels:
        print(f"  - {channel_id}")

    # Determine which channels to process
    channels_to_process = {}

    if args.all:
        channels_to_process = all_channels
    elif args.channel_id:
        if args.channel_id in all_channels:
            channels_to_process[args.channel_id] = all_channels[args.channel_id]
        else:
            print(f"\n❌ Channel '{args.channel_id}' not found in output directory")
            print(f"   Available channels: {', '.join(all_channels.keys())}")
            return

    # Process each channel
    total_stats = {
        'videos_uploaded': 0,
        'videos_failed': 0,
        'comments_uploaded': 0,
        'comments_failed': 0,
        'sub_comments_uploaded': 0,
        'sub_comments_failed': 0,
    }

    for channel_id, files in channels_to_process.items():
        stats = upload_channel_data(
            channel_id,
            files['videos'],
            files['comments'],
            files['sub_comments'],
            dry_run=args.dry_run
        )

        # Aggregate statistics
        total_stats['videos_uploaded'] += stats['videos_uploaded']
        total_stats['videos_failed'] += stats['videos_failed']
        total_stats['comments_uploaded'] += stats['comments_uploaded']
        total_stats['comments_failed'] += stats['comments_failed']
        total_stats['sub_comments_uploaded'] += stats['sub_comments_uploaded']
        total_stats['sub_comments_failed'] += stats['sub_comments_failed']

    # Print final summary
    print(f"\n{'=' * 70}")
    print("Upload Summary")
    print(f"{'=' * 70}")
    print(f"Channels Processed: {len(channels_to_process)}")
    print(f"\nVideos:")
    print(f"  ✅ Uploaded: {total_stats['videos_uploaded']}")
    if total_stats['videos_failed'] > 0:
        print(f"  ❌ Failed: {total_stats['videos_failed']}")
    print(f"\nComments:")
    print(f"  ✅ Uploaded: {total_stats['comments_uploaded']}")
    if total_stats['comments_failed'] > 0:
        print(f"  ❌ Failed: {total_stats['comments_failed']}")
    print(f"\nSub-Comments:")
    print(f"  ✅ Uploaded: {total_stats['sub_comments_uploaded']}")
    if total_stats['sub_comments_failed'] > 0:
        print(f"  ❌ Failed: {total_stats['sub_comments_failed']}")

    if args.dry_run:
        print(f"\n🔍 DRY RUN COMPLETE - No data was inserted")
    else:
        print(f"\n✅ Upload complete!")

    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
