-- Migration: Add processing status fields to reddit_posts table
-- Date: 2025-07-29

-- Add new fields for better URL fetch failure handling
ALTER TABLE reddit_posts 
ADD COLUMN processing_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN url_fetch_attempts INTEGER DEFAULT 0;

-- Add comment for documentation
COMMENT ON COLUMN reddit_posts.processing_status IS 'Processing status: pending, processed, url_fetch_failed, processing_failed';
COMMENT ON COLUMN reddit_posts.url_fetch_attempts IS 'Number of URL fetch attempts made for this post';

-- Update existing processed posts to have 'processed' status
UPDATE reddit_posts 
SET processing_status = 'processed' 
WHERE content_processed_at IS NOT NULL;

-- Add index for better query performance
CREATE INDEX idx_reddit_posts_processing_status ON reddit_posts(processing_status);