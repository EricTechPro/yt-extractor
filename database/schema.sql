-- ============================================================================
-- YouTube Comments Database Schema (Normalized)
-- ============================================================================
-- This schema defines three tables for storing YouTube videos, comments, and
-- replies extracted via the YouTube Data API v3. The structure matches the JSON
-- output from main.py for seamless data migration.
--
-- Tables:
--   1. videos        - Video metadata with full details
--   2. comments      - Top-level comments on videos
--   3. sub_comments  - Replies to parent comments
--
-- Key Design Decisions:
--   - Uses YouTube IDs as primary keys (TEXT) instead of UUIDs
--   - Normalized schema with proper foreign key relationships
--   - channel_id field to track which YouTube channel the data belongs to
--   - created_at timestamp to track when records were inserted
--   - Indexes on channel_id and foreign keys for query performance
-- ============================================================================

-- Uncomment these lines for development/testing to drop existing tables:
-- DROP INDEX IF EXISTS idx_videos_channel_id;
-- DROP INDEX IF EXISTS idx_comments_channel_id;
-- DROP INDEX IF EXISTS idx_comments_video_id;
-- DROP INDEX IF EXISTS idx_sub_comments_channel_id;
-- DROP INDEX IF EXISTS idx_sub_comments_video_id;
-- DROP INDEX IF EXISTS idx_sub_comments_parent_id;
-- DROP TABLE IF EXISTS sub_comments;
-- DROP TABLE IF EXISTS comments;
-- DROP TABLE IF EXISTS videos;

-- ============================================================================
-- Table: videos
-- ============================================================================
-- Stores comprehensive video metadata from YouTube.
-- Fields map directly to JSON output from [CHANNEL_ID]_videos.json
--
-- This is the parent table for both comments and sub_comments tables.
-- ============================================================================

CREATE TABLE IF NOT EXISTS videos (
    -- Primary key: YouTube's video ID (no UUID needed)
    youtube_video_id TEXT PRIMARY KEY,

    -- Channel tracking: Which YouTube channel this video belongs to
    -- Extracted from JSON filename pattern: [CHANNEL_ID]_videos.json
    channel_id TEXT NOT NULL,

    -- Video metadata (from YouTube API snippet)
    title TEXT,                           -- Video title
    description TEXT,                     -- Full video description
    tags TEXT[],                          -- Array of tag strings
    published_at TIMESTAMPTZ,            -- When the video was published (ISO 8601 format)
    channel_title TEXT,                  -- Channel name

    -- Video content details (from YouTube API contentDetails)
    duration TEXT,                        -- ISO 8601 duration (e.g., "PT1H2M10S")

    -- Video statistics (from YouTube API statistics)
    view_count INTEGER DEFAULT 0,        -- Number of views

    -- Audit field: When this record was inserted into the database
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient queries filtering by channel
CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);

-- ============================================================================
-- Table: comments
-- ============================================================================
-- Stores top-level comments posted on YouTube videos.
-- Fields map directly to JSON output from [CHANNEL_ID]_comments.json
--
-- RELATIONSHIP: video_id references videos.youtube_video_id
-- This establishes a foreign key relationship to the parent video.
-- ============================================================================

CREATE TABLE IF NOT EXISTS comments (
    -- Primary key: YouTube's comment ID (no UUID needed)
    youtube_comment_id TEXT PRIMARY KEY,

    -- Foreign key: Reference to parent video
    video_id TEXT NOT NULL,

    -- Channel tracking: Which YouTube channel this comment belongs to
    -- Extracted from JSON filename pattern: [CHANNEL_ID]_comments.json
    channel_id TEXT NOT NULL,

    -- Comment content and metadata (from JSON fields)
    comment TEXT,                         -- Comment text content
    date_post_comment TIMESTAMPTZ,       -- When the comment was posted (ISO 8601 format)
    likes_count INTEGER DEFAULT 0,       -- Number of likes on the comment

    -- Audit field: When this record was inserted into the database
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign key constraint to establish comment-video relationship
    CONSTRAINT fk_video
        FOREIGN KEY (video_id)
        REFERENCES videos(youtube_video_id)
        ON DELETE CASCADE  -- If video deleted, delete comments too
);

-- Index for efficient queries filtering by channel
CREATE INDEX IF NOT EXISTS idx_comments_channel_id ON comments(channel_id);

-- Index for efficient lookups by video (used in JOIN queries)
CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments(video_id);

-- ============================================================================
-- Table: sub_comments
-- ============================================================================
-- Stores replies to parent comments on YouTube videos.
-- Fields map directly to JSON output from [CHANNEL_ID]_sub_comments.json
--
-- RELATIONSHIPS:
--   - video_id references videos.youtube_video_id
--   - parent_comment_id references comments.youtube_comment_id
-- This establishes proper foreign key relationships between replies, their
-- parent comments, and the videos they belong to.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sub_comments (
    -- Primary key: YouTube's reply ID (no UUID needed)
    youtube_comment_id TEXT PRIMARY KEY,

    -- Foreign key: Reference to parent video
    video_id TEXT NOT NULL,

    -- Foreign key: Reference to parent comment
    parent_comment_id TEXT NOT NULL,

    -- Channel tracking: Which YouTube channel this reply belongs to
    -- Extracted from JSON filename pattern: [CHANNEL_ID]_sub_comments.json
    channel_id TEXT NOT NULL,

    -- Reply content and metadata (from JSON fields)
    sub_comment TEXT,                     -- Reply text content
    date_post_sub_comment TIMESTAMPTZ,   -- When the reply was posted (ISO 8601 format)
    like_count INTEGER DEFAULT 0,        -- Number of likes on the reply

    -- Audit field: When this record was inserted into the database
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign key constraints to establish relationships
    CONSTRAINT fk_video
        FOREIGN KEY (video_id)
        REFERENCES videos(youtube_video_id)
        ON DELETE CASCADE,  -- If video deleted, delete replies too

    CONSTRAINT fk_parent_comment
        FOREIGN KEY (parent_comment_id)
        REFERENCES comments(youtube_comment_id)
        ON DELETE CASCADE  -- If parent comment deleted, delete replies too
);

-- Index for efficient queries filtering by channel
CREATE INDEX IF NOT EXISTS idx_sub_comments_channel_id ON sub_comments(channel_id);

-- Index for efficient lookups by video (used in JOIN queries)
CREATE INDEX IF NOT EXISTS idx_sub_comments_video_id ON sub_comments(video_id);

-- Index for efficient lookups by parent comment (used in JOIN queries)
CREATE INDEX IF NOT EXISTS idx_sub_comments_parent_id ON sub_comments(parent_comment_id);

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
