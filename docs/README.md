# YouTube Comment Extractor

A robust Python tool for extracting all comments and replies from YouTube channels using the YouTube Data API v3. Features resumable operations, progress tracking, and comprehensive error handling.

## Features

- ✅ Extract all top-level comments and replies from a YouTube channel
- ✅ Resumable operation - automatically continues from where it left off
- ✅ Progress tracking with live terminal updates
- ✅ Graceful error handling (comments disabled, quota exceeded, rate limits)
- ✅ Atomic file writes - no data corruption on crashes
- ✅ Support for multiple channel URL formats (@username, /channel/ID, /c/custom, /user/username)
- ✅ UTF-8 support for international content
- ✅ Quota usage tracking
- ✅ Structured logging to file and console

## Quick Start

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR: venv\Scripts\activate  # On Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and add your YouTube API key

# 4. Run the extractor
python3 main.py
```

**Remember**: Always run `source venv/bin/activate` before using the script!

## Prerequisites

- Python 3.7 or higher
- YouTube Data API v3 key from Google Cloud Console

## Installation

### 1. Clone or download this repository

```bash
git clone <repository-url>
cd yt-extractor
```

### 2. Create and activate a virtual environment

**Important**: Always use a virtual environment to avoid dependency conflicts.

**On macOS/Linux:**

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

**On Windows:**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

You should see `(venv)` appear in your terminal prompt when the virtual environment is activated.

### 3. Install dependencies

**After activating the virtual environment**, install the required packages:

```bash
python3 -m pip install -r requirements.txt
```

**Note**: If you see "pip: command not found", make sure you:

1. Activated the virtual environment (step 2)
2. Use `python3 -m pip` instead of just `pip`

### 4. Get a YouTube Data API v3 Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services → Credentials**
4. Click **Create Credentials → API Key**
5. Enable **YouTube Data API v3** in the API Library
6. Copy your API key

### 5. Configure your API key

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API key
# YOUTUBE_API_KEY=your_actual_api_key_here
```

## Usage

### Activate Virtual Environment

**⚠️ IMPORTANT**: Always activate your virtual environment before running the script:

```bash
# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt when activated.

**When you're done**, deactivate the virtual environment:

```bash
deactivate
```

### Interactive Mode (Recommended)

Simply run the script and follow the prompts:

```bash
python3 src/main.py
```

You'll be prompted to enter a YouTube channel URL. The script accepts any of these formats:

- `https://www.youtube.com/@username`
- `https://www.youtube.com/channel/UCBR8-60-B28hp2BmDPdntcQ`
- `https://www.youtube.com/c/CustomName`
- `https://www.youtube.com/user/username`

### Command-Line Mode

You can also provide the channel URL directly:

```bash
python3 src/main.py --channel "https://www.youtube.com/@EricWTech"
```

Override the API key from command line:

```bash
python3 src/main.py --channel "https://www.youtube.com/@username" --api-key "YOUR_API_KEY"
```

## Output

The script creates an `output/` directory with two JSON files per channel:

### 1. `[CHANNEL_ID]_comments.json`

Contains all top-level comments:

```json
[
  {
    "comment": "This is a great video!",
    "videoTitle": "Video Title Here",
    "videoLink": "https://www.youtube.com/watch?v=video_id",
    "datePostComment": "2025-11-04T10:30:01Z",
    "likesCount": 125
  }
]
```

### 2. `[CHANNEL_ID]_sub_comments.json`

Contains all replies:

```json
[
  {
    "subComment": "Thanks for the feedback!",
    "parentCommentId": "parent_comment_id",
    "videoTitle": "Video Title Here",
    "videoLinkId": "video_id",
    "datePostSubComment": "2025-11-04T11:00:00Z",
    "likeCount": 5
  }
]
```

### 3. `[CHANNEL_ID]_processing.log`

Detailed processing log with timestamps and error messages.

## Supabase Integration

### Overview

In addition to local JSON storage, you can upload extracted comments to a Supabase PostgreSQL database for persistent storage, querying, and analysis.

### Database Schema

Two tables store the extracted data:

**`comments` table** (top-level comments):

| Column           | Type         | Description                         |
| ---------------- | ------------ | ----------------------------------- |
| id               | UUID         | Primary key (auto-generated)        |
| channel_id       | TEXT         | YouTube channel ID                  |
| comment          | TEXT         | Comment text content                |
| videoTitle       | TEXT         | Video title                         |
| videoLink        | TEXT         | Full YouTube video URL              |
| datePostComment  | TIMESTAMPTZ  | When comment was posted             |
| likesCount       | INTEGER      | Number of likes                     |
| created_at       | TIMESTAMPTZ  | When record was inserted (auto)     |

**`sub_comments` table** (replies):

| Column              | Type         | Description                         |
| ------------------- | ------------ | ----------------------------------- |
| id                  | UUID         | Primary key (auto-generated)        |
| channel_id          | TEXT         | YouTube channel ID                  |
| subComment          | TEXT         | Reply text content                  |
| parentCommentId     | TEXT         | YouTube's parent comment ID         |
| videoTitle          | TEXT         | Video title                         |
| videoLinkId         | TEXT         | YouTube video ID                    |
| datePostSubComment  | TIMESTAMPTZ  | When reply was posted               |
| likeCount           | INTEGER      | Number of likes                     |
| created_at          | TIMESTAMPTZ  | When record was inserted (auto)     |

Both tables have indexes on `channel_id` for efficient querying.

### Setup Instructions

#### 1. Create Supabase Account and Project

1. Go to [supabase.com](https://supabase.com/) and create a free account
2. Create a new project
3. Wait for the database to finish provisioning

#### 2. Deploy Database Schema

Run the SQL schema in your Supabase project:

1. Open your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of `database/schema.sql` from this repository
4. Paste and execute in the SQL Editor
5. Verify tables were created:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('comments', 'sub_comments');
```

#### 3. Get Supabase Credentials

1. In your Supabase project, go to **Settings → API**
2. Copy your **Project URL** (e.g., `https://xxxxx.supabase.co`)
3. Copy your **service_role key** (recommended) or **anon key**

**Note**: Use the `service_role` key for the upload script as it bypasses Row Level Security (RLS) policies.

#### 4. Configure Environment Variables

Add your Supabase credentials to `.env`:

```bash
# Existing YouTube API key
YOUTUBE_API_KEY=your_youtube_api_key

# Supabase credentials (new)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_service_role_or_anon_key
```

#### 5. Install Supabase Client

The `supabase` Python library is already included in `requirements.txt`. If you haven't installed dependencies yet:

```bash
source venv/bin/activate  # Activate virtual environment first
pip install -r requirements.txt
```

### Upload Script Usage

The `database/upload_to_supabase.py` script uploads JSON files from the `output/` directory to your Supabase database.

#### Upload Specific Channel

```bash
python3 database/upload_to_supabase.py --channel-id UCxxxxxx
```

This uploads both comments and sub-comments for the specified channel ID.

#### Upload All Channels

```bash
python3 database/upload_to_supabase.py --all
```

Processes all channels found in the `output/` directory.

#### Dry Run (Test Without Inserting)

```bash
python3 database/upload_to_supabase.py --channel-id UCxxxxxx --dry-run
```

Validates files and shows what would be uploaded without actually inserting data.

#### Custom Batch Size

```bash
python3 database/upload_to_supabase.py --all --batch-size 50
```

Default batch size is 100 records. Adjust if you encounter timeouts or rate limits.

#### Custom Output Directory

```bash
python3 database/upload_to_supabase.py --all --output-dir /path/to/output
```

### Upload Workflow

**Complete workflow from extraction to database:**

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Extract comments from YouTube
python3 main.py --channel "https://www.youtube.com/@username"

# 3. Upload to Supabase
python3 database/upload_to_supabase.py --channel-id UCxxxxxx

# 4. Verify in Supabase dashboard
# Go to Table Editor and check comments/sub_comments tables
```

### Features

- ✅ **Batch Insertion** - Uploads 100 records at a time for efficiency
- ✅ **Progress Tracking** - Real-time progress bars with tqdm
- ✅ **Error Handling** - Continues processing even if some batches fail
- ✅ **Duplicate Detection** - Warns if records already exist for a channel
- ✅ **Dry Run Mode** - Test without modifying database
- ✅ **Channel ID Tracking** - Automatically extracts and adds channel_id to records
- ✅ **Automatic Field Mapping** - Correctly maps JSON fields to database columns

### Querying Data in Supabase

Once uploaded, you can query your data using SQL in the Supabase SQL Editor:

**Get all comments for a specific channel:**

```sql
SELECT * FROM comments
WHERE channel_id = 'UCxxxxxx'
ORDER BY datePostComment DESC;
```

**Count comments by channel:**

```sql
SELECT channel_id, COUNT(*) as total_comments
FROM comments
GROUP BY channel_id
ORDER BY total_comments DESC;
```

**Get most liked comments:**

```sql
SELECT comment, videoTitle, likesCount
FROM comments
ORDER BY likesCount DESC
LIMIT 10;
```

**Get comments with their replies:**

```sql
SELECT
    c.comment,
    c.videoTitle,
    c.likesCount,
    COUNT(sc.id) as reply_count
FROM comments c
LEFT JOIN sub_comments sc ON sc.parentCommentId = c.id::text
GROUP BY c.id, c.comment, c.videoTitle, c.likesCount
HAVING COUNT(sc.id) > 0
ORDER BY reply_count DESC;
```

### Troubleshooting Supabase Integration

#### "Supabase credentials not found"

- Verify `.env` file exists and contains `SUPABASE_URL` and `SUPABASE_KEY`
- Check for extra spaces or quotes in the `.env` file
- Make sure you copied `.env.example` to `.env` and added your credentials

#### "Error initializing Supabase client"

- Verify `SUPABASE_URL` format is correct: `https://xxxxx.supabase.co`
- Verify `SUPABASE_KEY` is valid (copy from Supabase dashboard → Settings → API)
- Check your internet connection

#### "Permission denied" or "Insufficient privileges"

- You may be using the `anon` key instead of `service_role` key
- The `service_role` key has full database access (required for bulk inserts)
- Get it from: Supabase Dashboard → Settings → API → service_role key

#### "Table does not exist"

- Make sure you deployed `schema.sql` in the Supabase SQL Editor
- Verify tables exist: Run `\dt` in SQL Editor or check Table Editor
- Re-run the schema.sql if needed

#### Duplicate records

- The upload script doesn't prevent duplicates by default
- If you re-upload the same data, you'll get duplicate records
- The script warns you if records already exist for a channel
- To avoid duplicates, only upload once per channel extraction

#### Batch insert failures

- Check Supabase logs: Dashboard → Logs → Database
- Reduce batch size: `--batch-size 50`
- Verify data format matches database schema
- Check for NULL values in required fields

## Resumability

If the script is interrupted (Ctrl+C, crash, quota exceeded), simply run it again with the same channel URL. The script will:

1. Read the existing `[CHANNEL_ID]_comments.json` file
2. Identify which videos have already been processed
3. Skip those videos and continue with the rest
4. Append new comments to the existing files

**Note**: Progress is saved after each video is processed, so you'll only lose comments from the current video if interrupted.

## Quota Management

The YouTube Data API v3 has a default quota of **10,000 units per day**. This script tracks quota usage:

| Operation           | Cost (units)       | Notes                 |
| ------------------- | ------------------ | --------------------- |
| Get channel info    | 1                  | Once per run          |
| Get videos list     | 1 per 50 videos    | Pagination            |
| Get comments        | 1 per 100 comments | Pagination            |
| Get replies         | 1 per 100 replies  | Pagination            |
| Search by @username | 100                | Only for @handle URLs |

**Example**: A channel with 100 videos averaging 50 comments each (with 10% having replies) would cost approximately:

- Channel info: 1 unit
- Videos: 2 units (100 videos ÷ 50 per page)
- Comments: 50 units (5,000 comments ÷ 100 per page)
- Replies: ~5 units (estimated)
- **Total**: ~58 units

With 10,000 units/day, you can process approximately **170 channels of this size per day**.

## Error Handling

### Comments Disabled

If a video has comments disabled, the script logs a warning and continues with the next video.

### Quota Exceeded

If you hit the daily quota limit, the script:

1. Saves all progress up to that point
2. Displays a message indicating quota exhaustion
3. Exits gracefully
4. You can resume the next day

### Rate Limiting

The script automatically handles rate limits with exponential backoff:

- Retries up to 3 times
- Waits 2^attempt seconds between retries
- Adds random jitter to prevent thundering herd

### Network Issues

Transient network errors are automatically retried with exponential backoff.

## Troubleshooting

### "ModuleNotFoundError" or "No module named 'googleapiclient'"

- **Cause**: Virtual environment not activated or dependencies not installed
- **Solution**:
  1. Activate the virtual environment: `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\activate` (Windows)
  2. Verify you see `(venv)` in your terminal prompt
  3. Install dependencies: `pip install -r requirements.txt`

### "API key not found"

- Make sure you've created a `.env` file (copy from `.env.example`)
- Verify your API key is correctly set in the `.env` file
- Check that there are no extra spaces or quotes around the key

### "quotaExceeded" error

- You've hit the daily quota limit (10,000 units)
- Wait until the next day (quota resets at midnight Pacific Time)
- Run the script again to resume where you left off

### "Channel not found"

- Verify the channel URL is correct
- Some private or restricted channels may not be accessible
- Try accessing the channel in a browser to confirm it exists

### Missing comments

- Some videos may have comments disabled
- YouTube API may not return all comments in rare cases
- Check the `[CHANNEL_ID]_failed_replies.json` file for partial fetch issues

## Advanced Configuration

You can modify the `CONFIG` dictionary in `src/main.py` to customize:

```python
CONFIG = {
    'output_dir': 'output',           # Output directory path
    'max_results_videos': 50,         # Videos per API call (max 50)
    'max_results_comments': 100,      # Comments per API call (max 100)
    'retry_attempts': 3,              # Number of retry attempts
    'api_version': 'v3'               # YouTube API version
}
```

## Project Structure

```
yt-extractor/
├── src/                         # Core application
│   └── main.py                  # Main extraction script
├── database/                    # Database layer
│   ├── migrations/
│   │   └── 001_normalized_schema.sql  # Schema migration
│   ├── schema.sql               # Database schema for Supabase
│   ├── upload_to_supabase.py    # Supabase upload script
│   └── run_migration.py         # Migration runner
├── scripts/                     # Utility scripts
│   ├── verify_relationships.py  # Local data validation
│   ├── verify_supabase_data.py  # Remote data verification
│   └── clear_old_data.py        # Data cleanup utility
├── docs/                        # Documentation
│   ├── README.md                # User guide (this file)
│   ├── CLAUDE.md                # Developer guidance
│   ├── prompt.md                # Original requirements
│   └── SQL_AGENT_TEST_CASES.md  # SQL testing docs
├── output/                      # Generated data (gitignored)
│   ├── [CHANNEL_ID]_videos.json
│   ├── [CHANNEL_ID]_comments.json
│   └── [CHANNEL_ID]_sub_comments.json
├── venv/                        # Python virtual environment (gitignored)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── .env                         # Your API keys (gitignored)
└── .gitignore                   # Git ignore rules
```

## Best Practices

1. **Always activate the virtual environment** - Run `source venv/bin/activate` before every session to ensure proper dependency isolation
2. **Test with small channels first** - Verify everything works before processing large channels
3. **Monitor quota usage** - Check the quota usage displayed at the end of each run
4. **Run during off-peak hours** - Reduce the chance of rate limiting
5. **Keep logs** - Processing logs help debug issues
6. **Backup output files** - The JSON files are valuable data
7. **Use version control** - Track changes to the script (but never commit `.env`)

## Technical Details

### API Methods Used

- `channels().list()` - Get channel information
- `playlistItems().list()` - Get all videos from uploads playlist
- `commentThreads().list()` - Get top-level comments
- `comments().list()` - Get replies to comments

### Pagination

All API calls use cursor-based pagination with `nextPageToken` to handle large datasets.

### Atomic Writes

Files are written atomically using a temporary file + `os.replace()` to prevent corruption on crashes.

### Data Structure Matching

Output JSON files match the exact structure specified in `prompt.md` for compatibility with downstream tools.

## License

This project is provided as-is for educational and research purposes.

## Contributing

Contributions are welcome! Please ensure:

- Code follows existing style and patterns
- All functions have docstrings
- Error handling is comprehensive
- Changes are tested with real YouTube channels

## Support

For issues, questions, or feature requests, please check:

1. This README for common solutions
2. The processing log file for detailed error messages
3. YouTube Data API v3 documentation for API-specific issues

## Acknowledgments

- Built with the [Google API Python Client](https://github.com/googleapis/google-api-python-client)
- Uses [tqdm](https://github.com/tqdm/tqdm) for progress tracking
- Follows YouTube Data API v3 best practices
