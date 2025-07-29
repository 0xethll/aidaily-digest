-- Supabase Database Schema for Reddit AI Daily Digest (v2)
-- Updated to use reddit_id as primary keys for better performance and simplicity

-- Table for storing subreddit information
CREATE TABLE subreddits (
    name VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    subscribers INTEGER,
    active_users INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing Reddit submissions/posts
CREATE TABLE reddit_posts (
    reddit_id VARCHAR(20) PRIMARY KEY,
    subreddit_name VARCHAR(100) REFERENCES subreddits(name) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    score INTEGER DEFAULT 0,
    num_comments INTEGER DEFAULT 0,
    upvote_ratio DECIMAL(3,2),
    author VARCHAR(100),
    created_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    is_stickied BOOLEAN DEFAULT FALSE,
    is_nsfw BOOLEAN DEFAULT FALSE,
    is_self BOOLEAN DEFAULT FALSE,
    permalink TEXT,
    thumbnail TEXT,
    
    -- AI processing fields
    summary TEXT,
    summary_generated_at TIMESTAMP WITH TIME ZONE,
    content_type VARCHAR(50), -- news, discussion, tutorial, question, tool, research, etc.
    keywords TEXT[], -- array of extracted keywords
    content_processed_at TIMESTAMP WITH TIME ZONE,
    processing_status VARCHAR(20) DEFAULT 'pending', -- pending, processed, url_fetch_failed, processing_failed
    url_fetch_attempts INTEGER DEFAULT 0,
    
    -- Metadata
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing Reddit comments
CREATE TABLE reddit_comments (
    reddit_id VARCHAR(20) PRIMARY KEY,
    post_reddit_id VARCHAR(20) REFERENCES reddit_posts(reddit_id) ON DELETE CASCADE,
    parent_comment_reddit_id VARCHAR(20) REFERENCES reddit_comments(reddit_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    author VARCHAR(100),
    created_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    is_submitter BOOLEAN DEFAULT FALSE,
    depth INTEGER DEFAULT 0,
    
    -- Metadata
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for daily digest generation (keep UUID for internal use)
CREATE TABLE daily_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE UNIQUE NOT NULL,
    post_count INTEGER DEFAULT 0,
    summary TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    telegram_message_id BIGINT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Junction table for posts included in each digest
CREATE TABLE digest_posts (
    digest_id UUID REFERENCES daily_digests(id) ON DELETE CASCADE,
    post_reddit_id VARCHAR(20) REFERENCES reddit_posts(reddit_id) ON DELETE CASCADE,
    PRIMARY KEY (digest_id, post_reddit_id)
);

-- Create indexes for performance
CREATE INDEX idx_reddit_posts_subreddit_name ON reddit_posts(subreddit_name);
CREATE INDEX idx_reddit_posts_created_utc ON reddit_posts(created_utc);
CREATE INDEX idx_reddit_posts_score ON reddit_posts(score);
CREATE INDEX idx_reddit_posts_fetched_at ON reddit_posts(fetched_at);
CREATE INDEX idx_reddit_comments_post_reddit_id ON reddit_comments(post_reddit_id);
CREATE INDEX idx_reddit_comments_parent_comment_reddit_id ON reddit_comments(parent_comment_reddit_id);
CREATE INDEX idx_reddit_comments_created_utc ON reddit_comments(created_utc);
CREATE INDEX idx_reddit_comments_fetched_at ON reddit_comments(fetched_at);
CREATE INDEX idx_daily_digests_date ON daily_digests(date);

-- Insert the target subreddits
INSERT INTO subreddits (name, display_name) VALUES
    ('AI_Agents', 'AI_Agents'),
    ('artificial', 'artificial'),
    ('ClaudeAI', 'ClaudeAI'),
    ('huggingface', 'huggingface'),
    ('LangChain', 'LangChain'),
    ('LocalLLaMA', 'LocalLLaMA'),
    ('OpenAI', 'OpenAI'),
    ('PromptEngineering', 'PromptEngineering'),
    ('singularity', 'singularity');

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_subreddits_updated_at 
    BEFORE UPDATE ON subreddits 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reddit_posts_updated_at 
    BEFORE UPDATE ON reddit_posts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_digests_updated_at 
    BEFORE UPDATE ON daily_digests 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create a view for randomly selecting failed posts

CREATE OR REPLACE VIEW random_failed_posts AS
SELECT *
FROM reddit_posts
WHERE processing_status IN ('processing_failed', 'url_fetch_failed')
ORDER BY RANDOM();

-- Create function to increment URL fetch attempts
CREATE OR REPLACE FUNCTION increment_url_fetch_attempts(post_reddit_id text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    UPDATE public.reddit_posts 
    SET url_fetch_attempts = COALESCE(url_fetch_attempts, 0) + 1
    WHERE reddit_id = post_reddit_id;
    
    -- Return true if a row was updated
    RETURN FOUND;
END;
$$;