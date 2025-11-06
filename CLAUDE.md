# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python CLI tool that extracts all comments and replies from YouTube channels using the YouTube Data API v3. Features resumable operations, atomic file writes, quota tracking, and comprehensive error handling.

## Development Commands

### Setup and Installation

```bash
# Create virtual environment (first time only)
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
python3 -m pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your YouTube Data API v3 key
```

### Running the Script

```bash
# Activate venv first (if not already activated)
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Interactive mode (prompts for channel URL)
python3 main.py

# Command-line mode with channel URL
python3 main.py --channel "https://www.youtube.com/@username"

# Override API key from command line
python3 main.py --channel "https://www.youtube.com/@username" --api-key "YOUR_KEY"
```

### Testing Different Channel URL Formats

Test URL parsing with these formats:
```bash
python3 main.py --channel "https://www.youtube.com/@username"          # Handle format
python3 main.py --channel "https://www.youtube.com/channel/CHANNEL_ID" # Direct ID
python3 main.py --channel "https://www.youtube.com/c/CustomName"       # Custom URL
python3 main.py --channel "https://www.youtube.com/user/username"      # Legacy user
```

### Dependency Management

```bash
# Update requirements.txt after adding new packages
python3 -m pip freeze > requirements.txt

# Verify installed packages
python3 -m pip list
```

## Code Architecture

### Single-File Monolithic Design

The entire application is contained in `main.py` (~1000 lines) with clear section boundaries:
- **Imports** (lines 8-26): External dependencies and environment setup
- **Configuration** (lines 28-41): Centralized CONFIG dictionary
- **API Setup** (lines 43-92): YouTube service initialization and validation
- **Quota Tracking** (lines 94-134): Global quota usage monitoring
- **Utility Functions** (lines 136-454): Reusable helpers for parsing, file I/O, state management
- **API Functions** (lines 456-753): YouTube API interaction layer
- **Main Execution** (lines 755-1005): CLI argument parsing and orchestration loop

### Key Design Patterns

**Resumability Architecture:**
- State stored in existing JSON files (`[CHANNEL_ID]_comments.json`)
- `load_state()` parses existing comments to build processed videos set
- Main loop filters videos using `processed_videos_set` before processing
- Progress saved atomically after each video completes

**Atomic File Writes:**
- `atomic_write_json()` uses tempfile + `os.replace()` for crash-safe writes
- Ensures no data corruption even if script is killed during write
- Critical for resumability - partial writes would corrupt state

**API Quota Management:**
- Global `quota_used` tracker increments after successful API calls
- `QUOTA_COSTS` dictionary maps operation types to unit costs
- `track_quota()` called by `api_call_with_retry()` wrapper
- Final report shows quota usage and remaining daily allocation

**Error Handling Strategy:**
- `api_call_with_retry()` wrapper with exponential backoff for rate limits (429, 503)
- Special handling for `commentsDisabled` errors (skip video, continue)
- Special handling for `quotaExceeded` errors (graceful shutdown, save progress)
- `parse_http_error_reason()` extracts specific error reasons from HttpError

**Pagination Pattern:**
- All API calls use cursor-based pagination with `nextPageToken`
- While loop pattern: fetch page → process items → check for `nextPageToken` → repeat
- Applied consistently across videos, comments, and replies fetching

### Output Data Structures

**Two Separate JSON Files Per Channel:**

1. **`[CHANNEL_ID]_comments.json`**: Top-level comments
   ```json
   {
     "comment": "text",
     "videoTitle": "title",
     "videoLink": "https://youtube.com/watch?v=id",
     "datePostComment": "ISO 8601 timestamp",
     "likesCount": number
   }
   ```

2. **`[CHANNEL_ID]_sub_comments.json`**: Replies (note different field names!)
   ```json
   {
     "subComment": "text",
     "parentCommentId": "comment_id",
     "videoTitle": "title",
     "videoLinkId": "video_id",
     "datePostSubComment": "ISO 8601 timestamp",
     "likeCount": number
   }
   ```

**Critical Schema Differences:**
- Top-level: `"comment"` vs replies: `"subComment"`
- Top-level: `"likesCount"` vs replies: `"likeCount"`
- Top-level: `"videoLink"` (full URL) vs replies: `"videoLinkId"` (just ID)

### YouTube Data API v3 Usage

**API Methods:**
- `channels().list()`: Get channel info and uploads playlist ID
- `playlistItems().list()`: Paginate through all videos in uploads playlist
- `commentThreads().list()`: Get top-level comments with reply counts
- `comments().list()`: Get replies for a specific parent comment

**Quota Costs:**
- `channels.list`: 1 unit
- `playlistItems.list`: 1 unit per page (50 videos max)
- `commentThreads.list`: 1 unit per page (100 comments max)
- `comments.list`: 1 unit per page (100 replies max)
- `search.list`: 100 units (used for @handle and /c/custom URL resolution)

**Daily Quota:** 10,000 units (default) - quota resets at midnight Pacific Time

### Channel URL Parsing Logic

`get_channel_id_from_url()` handles four URL formats:
1. **Direct channel ID**: `/channel/CHANNEL_ID` → extract immediately
2. **@username handle**: `/@username` → use `search.list` API (100 units)
3. **Custom URL**: `/c/CustomName` → use `search.list` API (100 units)
4. **Legacy user**: `/user/username` → use `channels.list` with `forUsername` (1 unit)

### Progress Tracking and User Feedback

- Uses `tqdm` progress bar for video processing loop
- Displays: "Processing videos: 75/320 [=====>....] 23%"
- Resumption info printed at startup (processed videos count)
- Final report shows total comments, sub-comments, quota usage
- Warnings for comments disabled, failed reply fetches

## Common Development Tasks

### Modifying API Configuration

Edit `CONFIG` dictionary in main.py:
```python
CONFIG = {
    'output_dir': 'output',           # Change output location
    'max_results_videos': 50,         # Videos per API call (max 50)
    'max_results_comments': 100,      # Comments per API call (max 100)
    'retry_attempts': 3,              # Retry count for rate limits
    'api_version': 'v3',              # YouTube API version
    'daily_quota_limit': 10000        # Daily quota for tracking
}
```

### Adding New Output Fields

1. Locate the API response parsing section (e.g., `fetch_video_comments()`)
2. Extract additional fields from the API response snippet
3. Add fields to the comment dictionary structure
4. Update documentation in README.md with new schema

### Debugging API Issues

```bash
# Test API key validity
python3 -c "from googleapiclient.discovery import build; import os; from dotenv import load_dotenv; load_dotenv(); youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY')); print('API key valid')"

# Check quota usage from output
grep "Quota Usage" output/*.log

# Verify channel ID extraction
python3 -c "from main import get_channel_id_from_url; print(get_channel_id_from_url('YOUR_URL_HERE'))"
```

### Testing Resumability

```bash
# Start processing a large channel
python3 main.py --channel "https://youtube.com/@largechannel"

# Interrupt with Ctrl+C after a few videos
# Restart to verify resume
python3 main.py --channel "https://youtube.com/@largechannel"
# Should skip already processed videos
```

## Important Constraints and Behaviors

1. **No Partial Video Processing**: If interrupted mid-video, that video's comments are re-fetched on resume
2. **Atomic Progress Saves**: Progress saved only after each complete video
3. **Reply Count Validation**: Tracks discrepancies between expected and fetched reply counts in `[CHANNEL_ID]_failed_replies.json`
4. **UTF-8 Support**: All JSON files written with `ensure_ascii=False` for international content
5. **Rate Limiting**: Exponential backoff (2^attempt + jitter) for 429/503 errors
6. **No Duplicate Detection**: Same comment text on different videos treated as separate entries

## File Structure

```
yt-extractor/
├── main.py                       # Single monolithic application file
├── requirements.txt              # Python dependencies (3 packages)
├── .env.example                  # Template for API key
├── .env                         # User's API key (gitignored)
├── .gitignore                   # Excludes venv, .env, output/, etc.
├── README.md                    # User-facing documentation
├── prompt.md                    # Original project requirements
├── CLAUDE.md                    # This file
├── venv/                        # Python virtual environment (gitignored)
└── output/                      # Generated JSON files (gitignored)
    ├── [CHANNEL_ID]_comments.json
    ├── [CHANNEL_ID]_sub_comments.json
    ├── [CHANNEL_ID]_processing.log (if logging added)
    └── [CHANNEL_ID]_failed_replies.json (if discrepancies)
```

## Dependencies

- **google-api-python-client** (2.110.0): YouTube Data API v3 client library
- **tqdm** (4.66.1): Terminal progress bars
- **python-dotenv** (1.0.0): Environment variable management from .env files

## Troubleshooting

### "pip: command not found" Error

**Problem**: Running `pip install -r requirements.txt` outside virtual environment

**Solution**: Always activate venv first:
```bash
source venv/bin/activate  # macOS/Linux
python3 -m pip install -r requirements.txt
```

### API Key Issues

**Problem**: "API key not found" or "invalid API key" errors

**Solution**:
1. Verify `.env` file exists (copy from `.env.example`)
2. Check `YOUTUBE_API_KEY=your_key_here` format (no quotes, no spaces)
3. Enable YouTube Data API v3 in Google Cloud Console
4. Test with minimal API call (see "Debugging API Issues" above)

### Quota Exceeded Mid-Processing

**Problem**: Script stops with "quotaExceeded" error

**Solution**:
1. Wait for quota reset (midnight Pacific Time)
2. Re-run script with same channel URL - will automatically resume
3. Consider processing fewer channels per day or requesting quota increase

### Missing Comments

**Problem**: Fewer comments extracted than expected

**Solution**:
1. Check `[CHANNEL_ID]_failed_replies.json` for reply fetch issues
2. Some videos may have comments disabled (logged as warnings)
3. YouTube API may not return all comments in rare cases (API limitation)
4. Private/deleted comments not accessible via API

## GitHub Repository Preparation

Before committing to GitHub:
1. ✓ `.gitignore` excludes sensitive files (`.env`, `venv/`, `output/`)
2. ✓ `.env.example` provided as template
3. ✓ `requirements.txt` has pinned versions
4. ✓ `README.md` has comprehensive user documentation
5. ✓ `CLAUDE.md` has developer guidance
6. ✓ All code has docstrings and inline comments
7. ✓ No API keys or secrets in code
