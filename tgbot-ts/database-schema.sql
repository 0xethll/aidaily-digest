-- Additional tables needed for the Telegram bot functionality


-- User conversations table for storing chat context
CREATE TABLE IF NOT EXISTS user_conversations (
    user_id BIGINT PRIMARY KEY,
    context JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Security logs table
CREATE TABLE IF NOT EXISTS security_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_conversations_updated_at ON user_conversations(updated_at);
CREATE INDEX IF NOT EXISTS idx_security_logs_user_id ON security_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_security_logs_event_type ON security_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_security_logs_timestamp ON security_logs(timestamp);

-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';


CREATE TRIGGER update_user_conversations_updated_at BEFORE UPDATE ON user_conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Cleanup function for old rate limit records (optional, can be called periodically)
CREATE OR REPLACE FUNCTION cleanup_old_rate_limits()
RETURNS void AS $$
BEGIN
    DELETE FROM rate_limits WHERE created_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Cleanup function for old security logs (optional, can be called periodically)
CREATE OR REPLACE FUNCTION cleanup_old_security_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM security_logs WHERE timestamp < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Create bot_users table
CREATE TABLE bot_users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT,
    is_bot BOOLEAN NOT NULL DEFAULT FALSE,
    is_premium BOOLEAN,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked', 'deleted')),
    first_interaction_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_interaction_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    interaction_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create function to increment interaction count
CREATE OR REPLACE FUNCTION increment_user_interaction(p_user_id BIGINT)
RETURNS void AS $$
BEGIN
    UPDATE bot_users
    SET interaction_count = interaction_count + 1,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- If user doesn't exist yet, create with count 1
    IF NOT FOUND THEN
        INSERT INTO bot_users (user_id, first_interaction_at, last_interaction_at, interaction_count)
        VALUES (p_user_id, NOW(), NOW(), 1)
        ON CONFLICT (user_id) DO NOTHING;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create index for performance
CREATE INDEX idx_bot_users_status ON bot_users(status);
CREATE INDEX idx_bot_users_last_interaction ON bot_users(last_interaction_at);