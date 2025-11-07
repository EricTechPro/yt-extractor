-- ============================================================================
-- Migration Script: Normalized Schema for YouTube Comments
-- ============================================================================
-- This migration drops the old schema and creates the new normalized structure
-- with videos, comments, and sub_comments tables using YouTube IDs as PKs.
--
-- WARNING: This will DELETE all existing data in comments and sub_comments tables!
-- Make sure you have a backup before running this migration.
-- ============================================================================

-- Step 1: Drop old indexes
DROP INDEX IF EXISTS idx_comments_channel_id;
DROP INDEX IF EXISTS idx_comments_youtube_id;
DROP INDEX IF EXISTS idx_sub_comments_channel_id;
DROP INDEX IF EXISTS idx_sub_comments_parent_id;

-- Step 2: Drop old tables (CASCADE will drop foreign key constraints)
DROP TABLE IF EXISTS sub_comments CASCADE;
DROP TABLE IF EXISTS comments CASCADE;

-- Step 3: Create new normalized schema

-- ============================================================================
-- Table: videos
-- ============================================================================
CREATE TABLE IF NOT EXISTS videos (
    -- Primary key: YouTube's video ID (no UUID needed)
    youtube_video_id TEXT PRIMARY KEY,

    -- Channel tracking
    channel_id TEXT NOT NULL,

    -- Video metadata (from YouTube API snippet)
    title TEXT,
    description TEXT,
    tags TEXT[],
    published_at TIMESTAMPTZ,
    channel_title TEXT,

    -- Video content details
    duration TEXT,

    -- Video statistics
    view_count INTEGER DEFAULT 0,

    -- Audit field
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient queries filtering by channel
CREATE INDEX idx_videos_channel_id ON videos(channel_id);

-- ============================================================================
-- Table: comments
-- ============================================================================
CREATE TABLE IF NOT EXISTS comments (
    -- Primary key: YouTube's comment ID (no UUID needed)
    youtube_comment_id TEXT PRIMARY KEY,

    -- Foreign key: Reference to parent video
    video_id TEXT NOT NULL,

    -- Channel tracking
    channel_id TEXT NOT NULL,

    -- Comment content and metadata
    comment TEXT,
    date_post_comment TIMESTAMPTZ,
    likes_count INTEGER DEFAULT 0,

    -- Audit field
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign key constraint
    CONSTRAINT fk_video
        FOREIGN KEY (video_id)
        REFERENCES videos(youtube_video_id)
        ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_comments_channel_id ON comments(channel_id);
CREATE INDEX idx_comments_video_id ON comments(video_id);

-- ============================================================================
-- Table: sub_comments
-- ============================================================================
CREATE TABLE IF NOT EXISTS sub_comments (
    -- Primary key: YouTube's reply ID (no UUID needed)
    youtube_comment_id TEXT PRIMARY KEY,

    -- Foreign keys
    video_id TEXT NOT NULL,
    parent_comment_id TEXT NOT NULL,

    -- Channel tracking
    channel_id TEXT NOT NULL,

    -- Reply content and metadata
    sub_comment TEXT,
    date_post_sub_comment TIMESTAMPTZ,
    like_count INTEGER DEFAULT 0,

    -- Audit field
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign key constraints
    CONSTRAINT fk_video
        FOREIGN KEY (video_id)
        REFERENCES videos(youtube_video_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_parent_comment
        FOREIGN KEY (parent_comment_id)
        REFERENCES comments(youtube_comment_id)
        ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_sub_comments_channel_id ON sub_comments(channel_id);
CREATE INDEX idx_sub_comments_video_id ON sub_comments(video_id);
CREATE INDEX idx_sub_comments_parent_id ON sub_comments(parent_comment_id);

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- Verify tables were created successfully:
--
--   SELECT table_name FROM information_schema.tables
--   WHERE table_schema = 'public' AND table_name IN ('videos', 'comments', 'sub_comments');
--
--   SELECT indexname, tablename FROM pg_indexes
--   WHERE tablename IN ('videos', 'comments', 'sub_comments');
-- ============================================================================
