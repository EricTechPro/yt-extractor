"""
YouTube Comment Extraction Tool

This script extracts comments from all videos in a YouTube channel using the YouTube Data API v3.
It supports resumable operation and saves comments to JSON files in the output directory.
"""

# ============================================================================
# IMPORTS
# ============================================================================

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import os
import tempfile
import time
import random
import argparse
from urllib.parse import urlparse, parse_qs
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================================================
# CONFIGURATION
# ============================================================================

# Application configuration dictionary
# Centralized configuration for easy customization and maintenance
CONFIG = {
    'output_dir': 'output',              # Directory for storing JSON output files
    'max_results_videos': 50,            # Videos per API call (max 50 per YouTube API)
    'max_results_comments': 100,         # Comments per API call (max 100 per YouTube API)
    'retry_attempts': 3,                 # Number of retry attempts for rate limiting
    'api_version': 'v3',                 # YouTube Data API version
    'daily_quota_limit': 10000           # Default daily quota limit in units
}


# ============================================================================
# API CONFIGURATION
# ============================================================================

# Load API key from environment variable
# Set your API key in .env file: YOUTUBE_API_KEY=your_key_here
API_KEY = os.getenv("YOUTUBE_API_KEY")

# Validate API key is present
if not API_KEY or API_KEY == "your_api_key_here":
    print("=" * 70)
    print("ERROR: YouTube API key not found or not configured properly")
    print("=" * 70)
    print()
    print("Please follow these steps:")
    print("1. Copy .env.example to .env")
    print("   $ cp .env.example .env")
    print()
    print("2. Get your API key from Google Cloud Console:")
    print("   https://console.cloud.google.com/apis/credentials")
    print()
    print("3. Edit .env and add your API key:")
    print("   YOUTUBE_API_KEY=your_actual_api_key_here")
    print()
    print("4. Make sure YouTube Data API v3 is enabled in your project")
    print("=" * 70)
    exit(1)


# ============================================================================
# OUTPUT DIRECTORY SETUP
# ============================================================================

# Create output directory for storing comment JSON files
# exist_ok=True ensures the script doesn't fail if directory already exists (important for resumability)
os.makedirs(CONFIG['output_dir'], exist_ok=True)


# ============================================================================
# YOUTUBE API SERVICE INITIALIZATION
# ============================================================================

try:
    # Initialize YouTube Data API v3 service object
    youtube = build("youtube", CONFIG['api_version'], developerKey=API_KEY)
except Exception as e:
    print(f"Error initializing YouTube API service: {e}")
    print("Please verify your API key is valid and YouTube Data API v3 is enabled in Google Cloud Console")
    raise


# ============================================================================
# QUOTA TRACKING
# ============================================================================

# Global quota usage tracker
# YouTube Data API v3 has a default quota of 10,000 units per day
quota_used = 0

# API operation costs in quota units
QUOTA_COSTS = {
    'channels.list': 1,
    'playlistItems.list': 1,
    'commentThreads.list': 1,
    'comments.list': 1,
    'search.list': 100
}


def track_quota(operation_type):
    """
    Track quota usage for YouTube Data API v3 operations.

    YouTube Data API v3 has a daily quota limit (default 10,000 units).
    This function tracks the cumulative quota usage across all API calls
    to help users monitor their consumption.

    Parameters:
        operation_type (str): The API operation type (e.g., 'channels.list', 'search.list')

    Returns:
        int: The total quota used so far

    Example:
        track_quota('channels.list')  # Adds 1 unit
        track_quota('search.list')    # Adds 100 units
    """
    global quota_used
    cost = QUOTA_COSTS.get(operation_type, 0)
    quota_used += cost
    return quota_used


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_http_error_reason(http_error):
    """
    Extract the reason from an HttpError by parsing its content.

    The HttpError object contains a content attribute with JSON-encoded error details.
    This function safely parses the content and extracts the error reason.

    Parameters:
        http_error (HttpError): The HttpError exception object

    Returns:
        str or None: The error reason (e.g., 'commentsDisabled', 'quotaExceeded') or None if not found
    """
    try:
        error_content = json.loads(http_error.content)
        errors = error_content.get('error', {}).get('errors', [{}])
        if errors:
            return errors[0].get('reason')
        return None
    except (json.JSONDecodeError, AttributeError, IndexError, KeyError):
        return None


def api_call_with_retry(api_func, operation_type=None, max_retries=None):
    """
    Execute an API call with exponential backoff retry logic for transient errors.

    This function handles rate limiting (429) and service unavailability (503) errors
    by automatically retrying with exponential backoff. This follows YouTube API v3
    best practices for handling transient failures. Also tracks quota usage.

    Parameters:
        api_func (callable): A function that makes an API call and returns the response
        operation_type (str): The API operation type for quota tracking (e.g., 'channels.list')
        max_retries (int): Maximum number of retry attempts (default: from CONFIG)

    Returns:
        dict: The API response from the successful call

    Raises:
        HttpError: If all retry attempts fail or if the error is not retryable
        Exception: For non-HTTP errors

    Example:
        response = api_call_with_retry(
            lambda: youtube.commentThreads().list(videoId=video_id, part="snippet").execute(),
            operation_type='commentThreads.list'
        )
    """
    if max_retries is None:
        max_retries = CONFIG['retry_attempts']

    for attempt in range(max_retries):
        try:
            result = api_func()
            # Track quota usage on successful call
            if operation_type:
                track_quota(operation_type)
            return result
        except HttpError as e:
            # Check if this is a retryable error (rate limit or service unavailable)
            if e.resp.status in [429, 503]:
                if attempt < max_retries - 1:
                    # Calculate exponential backoff with jitter
                    # Formula: (2^attempt) + random(0, 1)
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"⚠️  Rate limited or service unavailable. Retrying in {wait_time:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    # Last attempt failed - re-raise the error
                    print(f"❌ Max retries ({max_retries}) exceeded. Giving up.")
                    raise
            else:
                # Non-retryable error - re-raise immediately
                raise
        except Exception as e:
            # Non-HTTP error - re-raise immediately
            raise


def create_video_link(video_id):
    """
    Create a standardized YouTube video URL from a video ID.

    This function provides a single source of truth for video link formatting,
    ensuring consistency across the application (DRY principle).

    Parameters:
        video_id (str): The YouTube video ID

    Returns:
        str: The complete YouTube video URL

    Example:
        >>> create_video_link("dQw4w9WgXcQ")
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    """
    return f"https://www.youtube.com/watch?v={video_id}"


def atomic_write_json(file_path, data):
    """
    Atomically write JSON data to a file using a temporary file and os.replace().

    This ensures that the file is never partially written or corrupted, even if the
    program crashes or is interrupted during the write operation.

    Parameters:
        file_path (str): The target file path to write to
        data (list or dict): The data to serialize as JSON

    Raises:
        Exception: If the write operation fails
    """
    # Create a temporary file in the same directory as the target file
    # This ensures the temp file is on the same filesystem for atomic replacement
    dir_path = os.path.dirname(file_path)

    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=dir_path, delete=False) as temp_file:
        temp_path = temp_file.name
        try:
            # Write the JSON data to the temporary file
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        except Exception as e:
            # Clean up the temporary file if writing fails
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise e

    # Atomically replace the target file with the temporary file
    # os.replace() is atomic on both POSIX and Windows systems
    os.replace(temp_path, file_path)


def get_channel_id_from_url(url):
    """
    Extract channel ID from various YouTube channel URL formats.

    Supported formats:
    - https://www.youtube.com/channel/CHANNEL_ID (direct channel ID)
    - https://www.youtube.com/@username (handle format)
    - https://www.youtube.com/c/CustomName (custom URL format)
    - https://www.youtube.com/user/username (legacy user format)

    Parameters:
        url (str): The full YouTube channel URL

    Returns:
        str: The extracted channel ID

    Raises:
        ValueError: If URL is invalid or channel cannot be found
    """
    try:
        # Parse the URL to extract components
        parsed_url = urlparse(url)

        # Validate that this is a YouTube URL
        if parsed_url.netloc not in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
            raise ValueError(f"Invalid YouTube URL: {url}")

        # Extract the path and split into segments
        path = parsed_url.path.strip('/')
        path_segments = path.split('/')

        if len(path_segments) < 1:
            raise ValueError(f"Invalid YouTube channel URL format: {url}")

        # Handle direct channel ID format: /channel/CHANNEL_ID
        if path_segments[0] == 'channel' and len(path_segments) >= 2:
            return path_segments[1]

        # Handle @username format: /@username
        if path_segments[0].startswith('@'):
            username = path_segments[0][1:]  # Remove the @ symbol
            # Use YouTube API to search for the channel by handle
            response = api_call_with_retry(
                lambda: youtube.search().list(
                    part="snippet",
                    q=f"@{username}",
                    type="channel",
                    maxResults=1
                ).execute(),
                operation_type='search.list'
            )

            if 'items' in response and len(response['items']) > 0:
                return response['items'][0]['snippet']['channelId']
            else:
                raise ValueError(f"Channel not found for handle: @{username}")

        # Handle custom URL format: /c/CustomName
        if path_segments[0] == 'c' and len(path_segments) >= 2:
            custom_name = path_segments[1]
            # Use YouTube API to search for the channel
            response = api_call_with_retry(
                lambda: youtube.search().list(
                    part="snippet",
                    q=custom_name,
                    type="channel",
                    maxResults=1
                ).execute(),
                operation_type='search.list'
            )

            if 'items' in response and len(response['items']) > 0:
                return response['items'][0]['snippet']['channelId']
            else:
                raise ValueError(f"Channel not found for custom name: {custom_name}")

        # Handle legacy user format: /user/username
        if path_segments[0] == 'user' and len(path_segments) >= 2:
            username = path_segments[1]
            # Use YouTube API channels().list with forUsername parameter
            response = api_call_with_retry(
                lambda: youtube.channels().list(
                    part="id",
                    forUsername=username
                ).execute(),
                operation_type='channels.list'
            )

            if 'items' in response and len(response['items']) > 0:
                return response['items'][0]['id']
            else:
                raise ValueError(f"Channel not found for username: {username}")

        # Fallback: try treating the last path segment as a potential channel ID
        # This handles edge cases where the URL might be malformed but still contains a valid ID
        potential_id = path_segments[-1]
        if potential_id and len(potential_id) == 24:  # YouTube channel IDs are typically 24 characters
            return potential_id

        raise ValueError(f"Unable to extract channel ID from URL: {url}")

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        else:
            raise ValueError(f"Error parsing URL: {str(e)}")


def load_state(comments_file):
    """
    Load existing state from comments file to support resumability.

    This function reads the existing comments JSON file (if it exists) and extracts:
    1. A set of video links that have already been processed (for skipping)
    2. The existing list of comments to append new comments to

    This enables the script to resume from where it left off if interrupted,
    avoiding duplicate API calls and processing.

    Parameters:
        comments_file (str): Path to the [CHANNEL_ID]_comments.json file

    Returns:
        tuple: (processed_videos_set, existing_comments_list)
            - processed_videos_set (set): Set of video links already processed
            - existing_comments_list (list): List of existing comment dictionaries
    """
    if os.path.exists(comments_file):
        try:
            with open(comments_file, 'r', encoding='utf-8') as f:
                existing_comments = json.load(f)

            # Extract all videoLink values from existing comments to create a set of processed videos
            # Each comment object has a 'videoLink' field (e.g., "https://www.youtube.com/watch?v=video_id")
            processed_videos_set = set(comment['videoLink'] for comment in existing_comments)

            return processed_videos_set, existing_comments

        except (json.JSONDecodeError, KeyError) as e:
            # If JSON is corrupted or structure is invalid, log warning and start fresh
            print(f"Warning: Could not parse existing comments file: {e}")
            print("Starting with fresh state...")
            return set(), []
    else:
        # File doesn't exist - this is the first run
        return set(), []


def load_sub_comments(sub_comments_file):
    """
    Load existing sub-comments (replies) from JSON file to support resumability.

    This function reads the existing sub-comments file and returns the list
    of sub-comment objects. Unlike load_state(), this doesn't create a processed
    videos set because resumption logic is based on top-level comments only.

    Parameters:
        sub_comments_file (str): Path to the [CHANNEL_ID]_sub_comments.json file

    Returns:
        list: List of existing sub-comment dictionaries (empty list if file doesn't exist)
    """
    if os.path.exists(sub_comments_file):
        try:
            with open(sub_comments_file, 'r', encoding='utf-8') as f:
                existing_sub_comments = json.load(f)
            return existing_sub_comments

        except json.JSONDecodeError as e:
            # If JSON is corrupted, log warning and start fresh
            print(f"Warning: Could not parse existing sub-comments file: {e}")
            print("Starting with fresh sub-comments state...")
            return []
    else:
        # File doesn't exist - this is the first run
        return []


def get_uploads_playlist_id(youtube, channel_id):
    """
    Retrieve the uploads playlist ID for a given YouTube channel.

    Every YouTube channel has an automatically generated "uploads" playlist that contains
    all videos uploaded to that channel. This function queries the YouTube Data API to
    retrieve the playlist ID from the channel's content details.

    The uploads playlist ID typically follows a pattern where the channel ID's "UC" prefix
    is replaced with "UU", but we always retrieve it via the API for reliability.

    Parameters:
        youtube (Resource): The YouTube API service object
        channel_id (str): The channel ID extracted from the URL

    Returns:
        str: The playlist ID for the channel's uploads

    Raises:
        ValueError: If the channel is not found or is inaccessible
        Exception: For API-related errors (network issues, invalid API key, etc.)
    """
    try:
        # Query the YouTube API for channel content details
        # part="contentDetails" retrieves the section containing related playlists
        response = api_call_with_retry(
            lambda: youtube.channels().list(
                part="contentDetails",
                id=channel_id
            ).execute(),
            operation_type='channels.list'
        )

        # Verify that the channel exists and returned data
        if 'items' not in response or len(response['items']) == 0:
            raise ValueError(f"Channel not found: {channel_id}")

        # Navigate the response structure to extract the uploads playlist ID
        # Structure: response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        return uploads_playlist_id

    except ValueError:
        # Re-raise ValueError as-is (channel not found)
        raise
    except Exception as e:
        # Catch and contextualize any API or network errors
        raise Exception(f"Error retrieving uploads playlist ID: {str(e)}")


def get_all_video_ids_and_titles(youtube, playlist_id):
    """
    Fetch all video IDs and titles from a playlist using pagination.

    YouTube playlists can contain thousands of videos, but the API returns results in pages
    with a maximum of 50 items per page. This function handles pagination automatically
    to retrieve all videos from the playlist.

    The function uses the YouTube Data API's playlistItems().list() endpoint with cursor-based
    pagination via the nextPageToken parameter.

    Parameters:
        youtube (Resource): The YouTube API service object
        playlist_id (str): The uploads playlist ID from get_uploads_playlist_id()

    Returns:
        list: List of dictionaries with structure [{"id": "video_id", "title": "video_title"}, ...]

    Raises:
        Exception: For API-related errors during video retrieval
    """
    videos = []  # Accumulator for all video data
    next_page_token = None  # Pagination cursor (None for first page)

    try:
        # Pagination loop: continues until there are no more pages to fetch
        while True:
            # Query the YouTube API for a page of playlist items
            response = api_call_with_retry(
                lambda: youtube.playlistItems().list(
                    part="snippet",  # Retrieve video metadata (contains video ID and title)
                    playlistId=playlist_id,  # Specify which playlist to query
                    maxResults=CONFIG['max_results_videos'],  # Fetch maximum items per page
                    pageToken=next_page_token  # Pagination cursor (None for first page)
                ).execute(),
                operation_type='playlistItems.list'
            )

            # Extract video data from the current page
            for item in response['items']:
                # Navigate the response structure to extract video ID and title
                # Video ID: item['snippet']['resourceId']['videoId']
                # Video title: item['snippet']['title']
                video_id = item['snippet']['resourceId']['videoId']
                video_title = item['snippet']['title']

                # Append the video data as a dictionary
                videos.append({
                    "id": video_id,
                    "title": video_title
                })

            # Check if there are more pages to fetch
            # If nextPageToken is absent, we've reached the last page
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break  # Exit the loop when no more pages exist

        return videos

    except Exception as e:
        # Catch and contextualize any API or network errors
        raise Exception(f"Error fetching videos from playlist {playlist_id}: {str(e)}")


def fetch_video_comments(youtube, video_id, video_title, video_link):
    """
    Retrieve all top-level comments for a specific video using pagination.

    This function handles the YouTube API's commentThreads().list() endpoint and returns
    structured comment data ready for JSON serialization. It also identifies which comments
    have replies to optimize subsequent reply fetching.

    The function uses cursor-based pagination to handle videos with large numbers of comments,
    fetching up to 100 comments per API call (the maximum allowed by the API).

    Parameters:
        youtube (Resource): The YouTube API service object
        video_id (str): The video ID to fetch comments from
        video_title (str): The video title (for comment structure)
        video_link (str): The full video URL (for comment structure)

    Returns:
        tuple: (comments_list, threads_with_replies)
            - comments_list (list of dict): List of comment dictionaries matching the structure
              in prompt.md lines 35-50
            - threads_with_replies (list of tuple): List of (parent_comment_id, reply_count)
              for comments that have replies

    Raises:
        googleapiclient.errors.HttpError: For API-related errors (re-raised to caller)
    """
    from googleapiclient.errors import HttpError

    comments_list = []  # Accumulator for all comments
    threads_with_replies = []  # Track comments that have replies
    next_page_token = None  # Pagination cursor (None for first page)

    try:
        # Pagination loop: continues until there are no more pages to fetch
        while True:
            # Query the YouTube API for a page of comment threads
            response = api_call_with_retry(
                lambda: youtube.commentThreads().list(
                    part="snippet",  # Retrieve comment metadata
                    videoId=video_id,  # Specify which video to query
                    maxResults=CONFIG['max_results_comments'],  # Fetch maximum items per page
                    textFormat="plainText",  # Get plain text without HTML formatting
                    pageToken=next_page_token  # Pagination cursor (None for first page)
                ).execute(),
                operation_type='commentThreads.list'
            )

            # Extract comment data from the current page
            for thread in response['items']:
                # Navigate to the top-level comment within the thread
                # Structure: thread['snippet']['topLevelComment']['snippet']
                top_level_comment = thread['snippet']['topLevelComment']['snippet']

                # Extract required fields from the comment snippet
                comment_text = top_level_comment['textDisplay']
                date_posted = top_level_comment['publishedAt']
                likes_count = top_level_comment['likeCount']

                # Create comment dictionary matching the exact structure from prompt.md
                comment_obj = {
                    "comment": comment_text,
                    "videoTitle": video_title,
                    "videoLink": video_link,
                    "datePostComment": date_posted,
                    "likesCount": likes_count
                }
                comments_list.append(comment_obj)

                # Check if this comment has replies
                # If totalReplyCount > 0, we need to fetch replies separately
                total_reply_count = thread['snippet']['totalReplyCount']
                if total_reply_count > 0:
                    parent_comment_id = thread['snippet']['topLevelComment']['id']
                    threads_with_replies.append((parent_comment_id, total_reply_count))

            # Check if there are more pages to fetch
            # If nextPageToken is absent, we've reached the last page
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break  # Exit the loop when no more pages exist

        return comments_list, threads_with_replies

    except HttpError as e:
        # Re-raise all HTTP errors to be handled by the main loop
        # This centralizes error handling in one place
        raise


def fetch_comment_replies(youtube, parent_comment_id, video_title, video_id):
    """
    Retrieve all replies (sub-comments) for a specific parent comment using pagination.

    This function handles the YouTube API's comments().list() endpoint and returns
    structured reply data matching the sub-comments JSON structure.

    The function uses cursor-based pagination to handle comments with large numbers of replies,
    fetching up to 100 replies per API call (the maximum allowed by the API).

    Parameters:
        youtube (Resource): The YouTube API service object
        parent_comment_id (str): The ID of the parent comment to fetch replies for
        video_title (str): The video title (needed for sub-comment structure)
        video_id (str): The video ID (needed for videoLinkId field)

    Returns:
        list: List of sub-comment dictionaries matching the structure in prompt.md lines 57-74
              Returns empty list if an error occurs

    Note:
        Field names differ from the comments file:
        - "subComment" (not "comment")
        - "likeCount" (not "likesCount")
        - "videoLinkId" (not "videoLink")
    """
    from googleapiclient.errors import HttpError

    sub_comments_list = []  # Accumulator for all replies
    next_page_token = None  # Pagination cursor (None for first page)

    try:
        # Pagination loop: continues until there are no more pages to fetch
        while True:
            # Query the YouTube API for a page of replies
            response = api_call_with_retry(
                lambda: youtube.comments().list(
                    part="snippet",  # Retrieve reply metadata
                    parentId=parent_comment_id,  # Specify which comment's replies to fetch
                    maxResults=CONFIG['max_results_comments'],  # Fetch maximum items per page
                    textFormat="plainText",  # Get plain text without HTML formatting
                    pageToken=next_page_token  # Pagination cursor (None for first page)
                ).execute(),
                operation_type='comments.list'
            )

            # Extract reply data from the current page
            for reply in response['items']:
                # Navigate to the reply snippet
                # Structure: reply['snippet']
                reply_snippet = reply['snippet']

                # Extract required fields from the reply snippet
                sub_comment_text = reply_snippet['textDisplay']
                date_posted = reply_snippet['publishedAt']
                like_count = reply_snippet['likeCount']

                # Create sub-comment dictionary matching the exact structure from prompt.md
                # Note: Field names differ from comments file
                sub_comment_obj = {
                    "subComment": sub_comment_text,
                    "parentCommentId": parent_comment_id,
                    "videoTitle": video_title,
                    "videoLinkId": video_id,
                    "datePostSubComment": date_posted,
                    "likeCount": like_count
                }
                sub_comments_list.append(sub_comment_obj)

            # Check if there are more pages to fetch
            # If nextPageToken is absent, we've reached the last page
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break  # Exit the loop when no more pages exist

        return sub_comments_list

    except HttpError as e:
        # Check if this is a quota exceeded error
        error_reason = parse_http_error_reason(e)
        if error_reason == 'quotaExceeded':
            # Re-raise quota errors so the main loop can handle graceful shutdown
            raise
        else:
            # Log a warning but don't crash - return empty list to allow processing to continue
            print(f"Warning: Error fetching replies for comment {parent_comment_id}: {e}")
            return []
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Warning: Unexpected error fetching replies for comment {parent_comment_id}: {e}")
        return []


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        # Parse command-line arguments
        parser = argparse.ArgumentParser(
            description='Extract all comments and replies from a YouTube channel',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Interactive mode (prompts for channel URL)
  python main.py

  # Command-line mode with channel URL
  python main.py --channel "https://www.youtube.com/@username"

  # Override API key from command line
  python main.py --channel "https://www.youtube.com/@username" --api-key "YOUR_KEY"

For more information, see README.md
            """
        )
        parser.add_argument(
            '--channel',
            type=str,
            help='YouTube channel URL (e.g., https://www.youtube.com/@username)'
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='YouTube Data API v3 key (overrides .env file)'
        )

        args = parser.parse_args()

        # Override API key if provided via command line
        if args.api_key:
            API_KEY = args.api_key
            # Re-initialize YouTube service with new API key
            youtube = build("youtube", CONFIG['api_version'], developerKey=API_KEY)

        # Step 1: User Input (Interactive or CLI)
        print()
        if args.channel:
            channel_url = args.channel.strip()
            print(f"Processing channel: {channel_url}")
        else:
            channel_url = input("Enter the YouTube channel URL: ").strip()
        print()

        # Step 2: Extract Channel ID
        try:
            channel_id = get_channel_id_from_url(channel_url)
            print(f"Processing channel: {channel_id}")
            print()
        except ValueError as e:
            print(f"Error: {e}")
            print("Please provide a valid YouTube channel URL and try again.")
            exit(1)

        # Step 3: Define File Paths
        # Channel-specific output files for storing comments and sub-comments
        comments_file = f"{CONFIG['output_dir']}/{channel_id}_comments.json"
        sub_comments_file = f"{CONFIG['output_dir']}/{channel_id}_sub_comments.json"

        # Step 4: Load Existing State
        processed_videos_set, master_comments_list = load_state(comments_file)
        master_sub_comments_list = load_sub_comments(sub_comments_file)

        # Display resumption status
        if processed_videos_set:
            print(f"Resuming: Found {len(processed_videos_set)} already processed videos")
            print(f"Existing comments: {len(master_comments_list)}")
            print(f"Existing sub-comments: {len(master_sub_comments_list)}")
        else:
            print("Starting fresh: No previous data found")
        print()

        # Step 5: Get Channel's Uploads Playlist ID
        try:
            uploads_playlist_id = get_uploads_playlist_id(youtube, channel_id)
            print(f"Found uploads playlist: {uploads_playlist_id}")
            print()
        except ValueError as e:
            print(f"Error: {e}")
            print("The channel may not exist or may be inaccessible.")
            exit(1)
        except Exception as e:
            print(f"Error retrieving channel information: {e}")
            print("Please verify your API key and network connection.")
            exit(1)

        # Step 6: Fetch All Videos from Channel
        try:
            all_videos = get_all_video_ids_and_titles(youtube, uploads_playlist_id)
            print(f"Found {len(all_videos)} total videos in channel")
            print()
        except Exception as e:
            print(f"Error fetching videos: {e}")
            print("Please check your API quota and try again.")
            exit(1)

        # Step 7: Filter Out Already Processed Videos
        videos_to_process = [
            v for v in all_videos
            if create_video_link(v['id']) not in processed_videos_set
        ]

        print(f"Videos to process: {len(videos_to_process)}")
        print(f"Videos already processed: {len(all_videos) - len(videos_to_process)}")
        print()

        # Handle edge case: all videos already processed
        if not videos_to_process:
            print("All videos have already been processed. Nothing to do.")
            exit(0)

        # Step 8: Main Comment Extraction Loop
        from googleapiclient.errors import HttpError

        # Track failed reply fetches for validation
        failed_reply_fetches = []

        for video in tqdm(videos_to_process, desc="Processing videos"):
            # Extract video data
            video_id = video['id']
            video_title = video['title']
            video_link = create_video_link(video_id)

            # Initialize temporary lists for this video's data
            new_comments = []
            new_sub_comments = []

            try:
                # Fetch top-level comments for this video
                comments_data, threads_with_replies = fetch_video_comments(
                    youtube, video_id, video_title, video_link
                )
                new_comments = comments_data

                # Fetch replies for comments that have them
                for parent_comment_id, reply_count in threads_with_replies:
                    try:
                        replies = fetch_comment_replies(
                            youtube, parent_comment_id, video_title, video_id
                        )
                        new_sub_comments.extend(replies)

                        # Validate that we fetched all expected replies
                        if len(replies) != reply_count:
                            failed_reply_fetches.append({
                                'parent_comment_id': parent_comment_id,
                                'video_id': video_id,
                                'video_title': video_title,
                                'video_link': video_link,
                                'expected_count': reply_count,
                                'fetched_count': len(replies),
                                'missing_count': reply_count - len(replies)
                            })
                    except Exception as e:
                        # Track complete fetch failures
                        failed_reply_fetches.append({
                            'parent_comment_id': parent_comment_id,
                            'video_id': video_id,
                            'video_title': video_title,
                            'video_link': video_link,
                            'expected_count': reply_count,
                            'fetched_count': 0,
                            'missing_count': reply_count,
                            'error': str(e)
                        })

            except HttpError as e:
                # Check for specific error reasons
                error_reason = parse_http_error_reason(e)

                if error_reason == 'commentsDisabled':
                    # Comments are disabled for this video - skip it
                    print(f"Skipping {video_title}: Comments disabled")
                    continue

                elif error_reason == 'quotaExceeded':
                    # API quota exceeded - stop gracefully
                    print()
                    print("=" * 70)
                    print("⚠️  API quota exceeded. Stopping gracefully...")
                    print("=" * 70)
                    print(f"Processed {len(master_comments_list)} comments and {len(master_sub_comments_list)} sub-comments")
                    print(f"📊 Quota used: {quota_used} units (of {CONFIG['daily_quota_limit']} daily limit)")
                    print()
                    print("Run the script again to resume from where you left off.")
                    print("Quota resets at midnight Pacific Time (PT).")
                    print("=" * 70)
                    break

                else:
                    # Other HTTP error - log and continue to next video
                    print(f"Error processing video {video_title}: {e}")
                    continue

            except Exception as e:
                # Unexpected error - log and continue to next video
                print(f"Error processing video {video_title}: {str(e)}")
                continue

            # Atomic progress saving after successfully processing this video
            # Extend the master lists with this video's data
            master_comments_list.extend(new_comments)
            master_sub_comments_list.extend(new_sub_comments)

            # Save comments file atomically
            atomic_write_json(comments_file, master_comments_list)

            # Save sub-comments file atomically
            atomic_write_json(sub_comments_file, master_sub_comments_list)

        # Step 9: Save Failed Reply Fetches (if any)
        if failed_reply_fetches:
            failed_replies_file = f"{CONFIG['output_dir']}/{channel_id}_failed_replies.json"
            atomic_write_json(failed_replies_file, failed_reply_fetches)
            print()
            print(f"⚠️  Warning: {len(failed_reply_fetches)} reply fetch discrepancies detected")
            print(f"   Details saved to: {failed_replies_file}")

        # Step 10: Completion Message
        print()
        print("=" * 70)
        print("Processing complete!")
        print("=" * 70)
        print(f"Total comments extracted: {len(master_comments_list)}")
        print(f"Total sub-comments extracted: {len(master_sub_comments_list)}")
        print(f"Data saved to: {comments_file} and {sub_comments_file}")
        print()
        print(f"📊 Quota Usage: {quota_used} units (of {CONFIG['daily_quota_limit']} daily limit)")
        print(f"   Remaining: {CONFIG['daily_quota_limit'] - quota_used} units ({((CONFIG['daily_quota_limit'] - quota_used) / CONFIG['daily_quota_limit'] * 100):.1f}%)")
        if failed_reply_fetches:
            print()
            print(f"⚠️  {len(failed_reply_fetches)} reply fetch discrepancies - see {failed_replies_file}")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Progress has been saved.")
        exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Please check your configuration and try again.")
        exit(1)
