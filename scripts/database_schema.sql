-- Supabase Database Schema for Reddit AI Daily Digest

-- Enable UUID extension for unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for storing subreddit information
CREATE TABLE subreddits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    subscribers INTEGER,
    active_users INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing Reddit submissions/posts
CREATE TABLE reddit_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reddit_id VARCHAR(20) UNIQUE NOT NULL,
    subreddit_id UUID REFERENCES subreddits(id) ON DELETE CASCADE,
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
    
    -- Metadata
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing Reddit comments (optional)
CREATE TABLE reddit_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reddit_id VARCHAR(20) UNIQUE NOT NULL,
    post_id UUID REFERENCES reddit_posts(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES reddit_comments(id) ON DELETE CASCADE,
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

-- Table for daily digest generation
CREATE TABLE daily_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    post_id UUID REFERENCES reddit_posts(id) ON DELETE CASCADE,
    PRIMARY KEY (digest_id, post_id)
);

-- Create indexes for performance
CREATE INDEX idx_reddit_posts_subreddit_id ON reddit_posts(subreddit_id);
CREATE INDEX idx_reddit_posts_created_utc ON reddit_posts(created_utc);
CREATE INDEX idx_reddit_posts_score ON reddit_posts(score);
CREATE INDEX idx_reddit_posts_reddit_id ON reddit_posts(reddit_id);
CREATE INDEX idx_reddit_comments_post_id ON reddit_comments(post_id);
CREATE INDEX idx_reddit_comments_created_utc ON reddit_comments(created_utc);
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

-- Row Level Security (RLS) policies if needed
-- ALTER TABLE reddit_posts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE reddit_comments ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE daily_digests ENABLE ROW LEVEL SECURITY;

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