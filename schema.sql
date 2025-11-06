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

    -- YouTube's unique comment identifier for establishing relationships
    youtube_comment_id TEXT UNIQUE,  -- YouTube's comment ID (e.g., "Ugye9E0Hgg9tSmVirzZ4AaABAg")

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

-- Index for efficient lookups by YouTube comment ID (used in FK relationships)
CREATE INDEX IF NOT EXISTS idx_comments_youtube_id ON comments(youtube_comment_id);

-- ============================================================================
-- Table: sub_comments
-- ============================================================================
-- Stores replies to parent comments on YouTube videos.
-- Fields map directly to JSON output from [CHANNEL_ID]_sub_comments.json
--
-- RELATIONSHIP: parentCommentId references comments.youtube_comment_id
-- This establishes a proper foreign key relationship between replies and
-- their parent comments, enabling queries like "get all replies for comment X"
-- ============================================================================

CREATE TABLE IF NOT EXISTS sub_comments (
    -- Primary key: Auto-generated UUID
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Channel tracking: Which YouTube channel this reply belongs to
    -- Extracted from JSON filename pattern: [CHANNEL_ID]_sub_comments.json
    channel_id TEXT NOT NULL,

    -- YouTube's unique identifier for this reply
    youtube_comment_id TEXT UNIQUE,  -- YouTube's reply ID (e.g., "UgxigSlcDUNv4vZ5FwN4AaABAg.A1B2C3D4E5F6G7H8I9J0")

    -- Reply content and metadata (from JSON fields)
    subComment TEXT,                      -- Reply text content
    parentCommentId TEXT,                 -- YouTube's parent comment ID - FK to comments.youtube_comment_id
    videoTitle TEXT,                      -- Title of the video
    videoLinkId TEXT,                     -- YouTube video ID (just the ID, not full URL)
    datePostSubComment TIMESTAMPTZ,       -- When the reply was posted (ISO 8601 format)
    likeCount INTEGER DEFAULT 0,          -- Number of likes on the reply

    -- Audit field: When this record was inserted into the database
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign key constraint to establish parent-child relationship
    CONSTRAINT fk_parent_comment
        FOREIGN KEY (parentCommentId)
        REFERENCES comments(youtube_comment_id)
        ON DELETE CASCADE  -- If parent comment deleted, delete replies too
);

-- Index for efficient queries filtering by channel
CREATE INDEX IF NOT EXISTS idx_sub_comments_channel_id ON sub_comments(channel_id);

-- Index for efficient lookups by parent comment (used in JOIN queries)
CREATE INDEX IF NOT EXISTS idx_sub_comments_parent_id ON sub_comments(parentCommentId);

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
