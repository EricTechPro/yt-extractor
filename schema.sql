-- ============================================================================
-- YouTube Comments Database Schema
-- ============================================================================
-- This schema defines two tables for storing YouTube comments and replies
-- extracted via the YouTube Data API v3. The structure matches the JSON
-- output from main.py for seamless data migration.
--
-- Tables:
--   1. comments      - Top-level comments on videos
--   2. sub_comments  - Replies to parent comments
--
-- Both tables include:
--   - UUID primary keys with auto-generation
--   - channel_id field to track which YouTube channel the data belongs to
--   - created_at timestamp to track when records were inserted
--   - Indexes on channel_id for query performance
-- ============================================================================

-- Uncomment these lines for development/testing to drop existing tables:
-- DROP INDEX IF EXISTS idx_comments_channel_id;
-- DROP INDEX IF EXISTS idx_sub_comments_channel_id;
-- DROP TABLE IF EXISTS sub_comments;
-- DROP TABLE IF EXISTS comments;

-- ============================================================================
-- Table: comments
-- ============================================================================
-- Stores top-level comments posted on YouTube videos.
-- Fields map directly to JSON output from [CHANNEL_ID]_comments.json
--
-- Note: Requires the pgcrypto extension for gen_random_uuid()
-- This is enabled by default in Supabase projects.
-- ============================================================================

CREATE TABLE IF NOT EXISTS comments (
    -- Primary key: Auto-generated UUID
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Channel tracking: Which YouTube channel this comment belongs to
    -- Extracted from JSON filename pattern: [CHANNEL_ID]_comments.json
    channel_id TEXT NOT NULL,

    -- Comment content and metadata (from JSON fields)
    comment TEXT,                    -- Comment text content
    videoTitle TEXT,                 -- Title of the video
    videoLink TEXT,                  -- Full YouTube video URL (https://youtube.com/watch?v=...)
    datePostComment TIMESTAMPTZ,     -- When the comment was posted (ISO 8601 format)
    likesCount INTEGER DEFAULT 0,    -- Number of likes on the comment

    -- Audit field: When this record was inserted into the database
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient queries filtering by channel
CREATE INDEX IF NOT EXISTS idx_comments_channel_id ON comments(channel_id);

-- ============================================================================
-- Table: sub_comments
-- ============================================================================
-- Stores replies to parent comments on YouTube videos.
-- Fields map directly to JSON output from [CHANNEL_ID]_sub_comments.json
--
-- IMPORTANT: parentCommentId references YouTube's internal comment ID system,
-- NOT the UUID primary key in the comments table. YouTube's comment IDs are
-- opaque strings that cannot be reliably joined to our database records.
-- If you need to establish relationships, consider storing parentCommentId
-- in the comments table and using it for joins.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sub_comments (
    -- Primary key: Auto-generated UUID
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Channel tracking: Which YouTube channel this reply belongs to
    -- Extracted from JSON filename pattern: [CHANNEL_ID]_sub_comments.json
    channel_id TEXT NOT NULL,

    -- Reply content and metadata (from JSON fields)
    subComment TEXT,                      -- Reply text content
    parentCommentId TEXT,                 -- YouTube's parent comment ID (not our UUID!)
    videoTitle TEXT,                      -- Title of the video
    videoLinkId TEXT,                     -- YouTube video ID (just the ID, not full URL)
    datePostSubComment TIMESTAMPTZ,       -- When the reply was posted (ISO 8601 format)
    likeCount INTEGER DEFAULT 0,          -- Number of likes on the reply

    -- Audit field: When this record was inserted into the database
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient queries filtering by channel
CREATE INDEX IF NOT EXISTS idx_sub_comments_channel_id ON sub_comments(channel_id);

-- ============================================================================
-- Schema Creation Complete
-- ============================================================================
-- Verify tables and indexes were created successfully:
--
--   SELECT table_name FROM information_schema.tables
--   WHERE table_schema = 'public' AND table_name IN ('comments', 'sub_comments');
--
--   SELECT indexname, tablename FROM pg_indexes
--   WHERE tablename IN ('comments', 'sub_comments');
--
-- Next Steps:
--   - Run verification queries (see create_tables.md)
--   - Proceed to Phase 3: Create upload_to_supabase.py script
-- ============================================================================
