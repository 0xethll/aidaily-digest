# AI Daily Digest Telegram Bot

A Telegram bot that automatically sends daily curated summaries of AI-related content from Reddit and provides interactive chat functionality powered by LLM.

## Features

> **Automated Daily Digests**: Sends organized summaries of the best AI content from Reddit communities  
=¬ **AI-Powered Chat**: Interactive conversations about AI topics using advanced LLM  
=Ê **Content Statistics**: View processing statistics and digest history  
= **Real-time Processing**: Integrates with the content processing pipeline  

## Supported Subreddits

- r/artificial - General AI discussions and news
- r/OpenAI - OpenAI-specific content and developments  
- r/ClaudeAI - Anthropic's Claude AI discussions
- r/LocalLLaMA - Local language model developments
- r/LangChain - LangChain framework discussions
- r/AI_Agents - AI agent development and applications
- r/PromptEngineering - Prompt engineering techniques
- r/singularity - AI singularity and futurism discussions

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- A Telegram bot token (from @BotFather)
- Supabase database (configured with the schema from `../scripts/sql/database_schema.sql`)
- Fireworks AI API key (for LLM functionality)

### 2. Create a Telegram Bot

1. Message @BotFather on Telegram
2. Use `/newbot` command and follow instructions
3. Save the bot token for configuration

### 3. Install Dependencies

```bash
uv sync
```

### 4. Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_ADMIN_CHAT_IDS=123456789  # Your Telegram user ID
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key  
FIREWORKS_API_KEY=your_fireworks_api_key
```

### 5. Getting Your Telegram Chat ID

To receive daily digests, you need your Telegram chat ID:

1. Start a chat with @userinfobot on Telegram
2. It will respond with your user ID
3. Add this ID to `TELEGRAM_ADMIN_CHAT_IDS` in your `.env` file

### 6. Run the Bot

```bash
uv run python main.py
```

## Bot Commands

- `/start` - Get started and see welcome message
- `/help` - Show help and available commands  
- `/stats` - View content processing statistics
- `/digest` - Get information about the latest digest
- `/test_digest` - Generate and send a test digest (admin only)

## Chat Functionality

The bot supports natural language conversations about AI topics. Just send any message to start chatting! The bot can:

- Answer questions about AI developments and trends
- Explain complex AI concepts
- Discuss recent research and breakthroughs
- Provide insights about AI tools and applications
- Chat about the future of AI

## Daily Digest Schedule

By default, the bot sends daily digests at 08:00 UTC. You can configure this by setting the `DIGEST_TIME_UTC` environment variable.

## Architecture

The bot consists of several key modules:

- **`main.py`** - Main bot application with command handlers and scheduling
- **`config.py`** - Configuration management and environment variable loading
- **`database.py`** - Database operations for fetching processed content
- **`digest_generator.py`** - Formats organized daily digest messages
- **`chat_handler.py`** - LLM-powered chat functionality

## Integration with Content Pipeline

This bot integrates with the existing content processing pipeline:

1. **Reddit Fetcher** (`../scripts/src/reddit_fetcher.py`) - Fetches posts from subreddits
2. **Content Processor** (`../scripts/src/content_processor.py`) - Processes and categorizes content using LLM
3. **Telegram Bot** (this project) - Generates digests and provides chat functionality

## Production Deployment

For production deployment:

1. Set up webhook instead of polling (optional)
2. Use a process manager like systemd or Docker
3. Configure logging and monitoring
4. Set up database backups

Example systemd service:

```ini
[Unit]
Description=AI Daily Digest Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/tgbot
ExecStart=/path/to/uv/run python main.py
Restart=always
RestartSec=10
Environment=PATH=/path/to/your/env

[Install]
WantedBy=multi-user.target
```

## Contributing

Feel free to contribute by:

- Adding new features or improvements
- Fixing bugs or issues
- Improving documentation
- Adding tests

## License

This project is part of the AI Daily Digest system.