-- Add twitter_sent field to reddit_posts table
-- This field will track whether a post has been tweeted to prevent duplicates

ALTER TABLE reddit_posts 
ADD COLUMN twitter_sent BOOLEAN DEFAULT FALSE;

-- Add index for efficient querying of posts that haven't been tweeted
CREATE INDEX idx_reddit_posts_twitter_sent ON reddit_posts(twitter_sent);

-- Add a timestamp field to track when the tweet was sent
ALTER TABLE reddit_posts 
ADD COLUMN twitter_sent_at TIMESTAMP WITH TIME ZONE;