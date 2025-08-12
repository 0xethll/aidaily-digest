-- Migration: Add Reddit push tracking field to reddit_posts table
-- Date: 2025-08-12

-- Add boolean field for tracking Reddit post pushes to Telegram
ALTER TABLE reddit_posts 
ADD COLUMN is_pushed BOOLEAN DEFAULT FALSE;

-- Add comment for documentation
COMMENT ON COLUMN reddit_posts.is_pushed IS 'Whether this post has been pushed to Telegram users';
