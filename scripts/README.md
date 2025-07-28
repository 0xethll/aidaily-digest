# Reddit AI Daily Digest - Data Fetcher

This module fetches daily submissions from AI-related subreddits and stores them in Supabase for processing into daily digest content.

## Features

- Fetches submissions from 9 AI-focused subreddits
- Implements Reddit API rate limiting and error handling
- Stores data in Supabase with comprehensive schema
- Filters content based on quality metrics
- Provides daily statistics and monitoring
- Supports automated daily scheduling

## Target Subreddits

- r/AI_Agents
- r/artificial
- r/ClaudeAI
<!-- - r/huggingface -->
- r/LangChain
- r/LocalLLaMA
- r/OpenAI
- r/PromptEngineering
- r/singularity

## Setup

### 1. Install Dependencies

```bash
uv sync
```

### 2. Database Setup

1. Create a new Supabase project
2. Run the SQL schema from `database_schema.sql` in your Supabase SQL editor
3. Get your Supabase URL and anon key from the project dashboard

### 3. Reddit API Setup

1. Go to https://www.reddit.com/prefs/apps
2. Create a new "script" application
3. Note down your client ID and client secret

### 4. Environment Configuration

1. Copy `.env.example` to `.env`
2. Fill in your Reddit and Supabase credentials:

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 5. Test the Setup

```bash
uv run reddit_fetcher.py
```

## Usage

### Manual Fetch

Run a one-time fetch of all subreddits:

```bash
uv run reddit_fetcher.py
```

### Daily Automated Fetch

Run the daily fetch script:

```bash
uv run run_daily_fetch.py
```

### Scheduling with Cron

Add to your crontab for daily execution at 8 AM:

```bash
# Add this line to your crontab (crontab -e)
0 8 * * * cd /path/to/scripts && python run_daily_fetch.py
```

## Configuration

### Reddit API Limits

- 60 requests per minute for authenticated users
- The fetcher implements automatic rate limiting and retries
- Waits up to 5 minutes for rate limit resets

### Content Filtering

Posts are filtered based on:

- Minimum score threshold (5 points)
- Age (last 24 hours only)
- Quality checks (not deleted/removed, sufficient title length)
- Excludes stickied posts

### Database Schema

The Supabase schema includes:

- `subreddits`: Target subreddit information
- `reddit_posts`: Individual submissions with metadata
- `reddit_comments`: Comments (optional)
- `daily_digests`: Daily digest generation tracking
- `digest_posts`: Junction table for digest composition

## Monitoring

- Logs are written to `reddit_fetch.log`
- Console output provides real-time progress
- Daily statistics available via `get_daily_stats()`

## Error Handling

- Automatic retry on rate limits
- Graceful degradation if individual subreddits fail
- Comprehensive logging for debugging
- Duplicate detection prevents re-fetching

## Files

- `reddit_fetcher.py`: Main fetcher class and logic
- `run_daily_fetch.py`: Daily execution script
- `database_schema.sql`: Supabase database schema
- `.env.example`: Environment variables template
- `reddit_fetch.log`: Runtime logs (generated)

## Next Steps

After setting up the fetcher:

1. **LLM Integration**: Add OpenAI/Claude API for post summarization
2. **Telegram Bot**: Create bot for daily digest delivery
3. **Mini App**: Build Telegram Mini App for user interaction
4. **Scheduling**: Set up automated daily runs
5. **Monitoring**: Add alerting for failed fetches
