-- Create a view for randomly selecting failed posts

-- Alternative approach if TABLESAMPLE doesn't work well:
CREATE OR REPLACE VIEW random_failed_posts AS
SELECT *
FROM reddit_posts
WHERE processing_status IN ('processing_failed', 'url_fetch_failed')
ORDER BY RANDOM();