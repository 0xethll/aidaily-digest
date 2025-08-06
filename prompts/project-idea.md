I’m planning a new project:

1. Fetch and store AI related top Reddit posts and their comments every 2 hours. Target Subreddits:

- r/AI_Agents
- r/artificial
- r/ClaudeAI
- r/LangChain
- r/LocalLLaMA
- r/OpenAI
- r/PromptEngineering
- r/singularity

2. Build a Telegram Mini App that automatically pushes a daily digest of those posts, each summarized by an LLM.
3. Let users chat directly with the Mini App, which is powered by the same LLM.

@scripts/sql/database_schema.sql is the database schema.
The code that gets data from Reddit is mostly in @scripts/src/reddit_fetcher.py.
The code responsible for processing the content is primarily located at @scripts/src/content_processor.py.

The fetched content will be processed by an LLM to categorize, extract keywords and summarize.

Categorization includes:

- news: Breaking news, announcements, industry updates
- discussion: Community discussions, debates, opinions
- tutorial: How-to guides, educational content, explanations
- question: Questions seeking help or information
- tool: Software tools, applications, libraries
- research: Academic papers, studies, technical research
- showcase: Projects, demos, personal work
- other: Content that doesn't fit other categories

I have used uv init tgbot to create a new directory named @tgbot for my Telegram bot and installed the python-telegram-bot library. Could you please help me complete the bot's code, you can use Context7 to reference the latest python-telegram-bot documentation?

I changed my mind and decided to deploy the Telegram bot to the Cloudflare building with Grammy webhook callback. I have fllowed the tutorial of hosting a `hello world` Telegram bot on Cloudflare Workers, the code is in @tgbot-ts. Help me complete the bot's code, you can use Context7 to reference the latest Grammy documentation?

Think carefully about how to make the daily pushed content organized and interesting.

1. Organizing Daily Pushes: How should I structure the daily content that is pushed to users to ensure it is well-organized and easy to navigate?

2. Processing Fetched Content: What are the best practices for handling and processing the fetched content to maintain quality and relevance?

3. Enhancing Content Appeal: How can I make the content more engaging and attractive to users to increase their interest and interaction?

Here it is the reddit_posts table schema:

```
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
```

I think there is no need to generateDigest. You can push the top five posts daily not every 2 hours. But there are some points need to be considered.

1. What time of day to push the daily digest?
2. Is it more reasonable to push yesterday's posts today? But yesterday's posts were posted late and the scores may not be high.
3. Except the daily post, is it worth checking the database for high-scoring news every two hours and then pushing it to users?
