# AI Daily Digest

An automated system that fetches AI news from Reddit, processes content with LLM, and delivers daily digests through a Telegram bot.

![AI Daily Digest](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![TypeScript](https://img.shields.io/badge/typescript-5.5%2B-blue)
![Cloudflare Workers](https://img.shields.io/badge/deploy-cloudflare%20workers-orange)

## 🚀 Features

### 📊 Data Collection

- **Reddit Integration**: Fetches top posts from 8+ AI-focused subreddits
- **Smart Filtering**: Quality-based content filtering with configurable thresholds
- **Rate Limited**: Respects Reddit API limits with automatic retry mechanisms
- **Comment Support**: Optional deep comment fetching with depth control

### 🤖 AI Processing

- **LLM Summarization**: Uses Fireworks AI for intelligent content summarization
- **Auto Categorization**: Classifies content into 8 categories (news, tutorial, research, etc.)
- **Keyword Extraction**: Automatically extracts relevant keywords
- **URL Content Fetching**: Intelligently fetches and processes linked article content

### 📱 Telegram Bot

- **Daily Digests**: Automated daily AI news summaries
- **Interactive Chat**: AI-powered conversations about AI topics
- **User Management**: Tracks users, handles blocked users, admin functions
- **Scheduled Delivery**: Configurable digest delivery times

### 🏗️ Infrastructure

- **Supabase Backend**: PostgreSQL database with real-time features
- **Serverless Deployment**: Cloudflare Workers for global performance
- **Systemd Integration**: Production-ready service management
- **Monitoring**: Comprehensive logging and error handling

## 🎯 Target Subreddits

- r/AI_Agents
- r/artificial
- r/ClaudeAI
- r/LangChain
- r/LocalLLaMA
- r/OpenAI
- r/PromptEngineering
- r/singularity

## 📋 Content Categories

| Category       | Description                                      |
| -------------- | ------------------------------------------------ |
| **news**       | Breaking news, announcements, industry updates   |
| **discussion** | Community discussions, debates, opinions         |
| **tutorial**   | How-to guides, educational content, explanations |
| **question**   | Questions seeking help or information            |
| **tool**       | Software tools, applications, libraries          |
| **research**   | Academic papers, studies, technical research     |
| **showcase**   | Projects, demos, personal work                   |
| **other**      | Content that doesn't fit other categories        |

## 🛠️ Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account
- Reddit API credentials
- Fireworks AI API key
- Telegram Bot Token
- Cloudflare account (for bot deployment)

### 1. Clone Repository

```bash
git clone <repository-url>
cd aidaily-digest
```

### 2. Reddit Fetcher Setup

1. Navigate to the scripts directory:

```bash
cd scripts
```

2. Install Python dependencies:

```bash
uv sync
```

3. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:

```bash
# Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key

# Fireworks AI
FIREWORKS_API_KEY=your_fireworks_api_key
FIREWORKS_MODEL=accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new
```

### 3. Telegram Bot Setup

1. Navigate to the bot directory:

```bash
cd ../tgbot-ts
```

2. Install dependencies:

```bash
npm install
```

3. Configure Cloudflare Workers secrets:

```bash
npx wrangler secret put BOT_TOKEN
npx wrangler secret put SUPABASE_URL
npx wrangler secret put SUPABASE_KEY
npx wrangler secret put FIREWORKS_API_KEY
npx wrangler secret put FIREWORKS_MODEL
```

4. Deploy to Cloudflare Workers:

```bash
npm run deploy
```

5. Set webhook URL:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-worker.your-subdomain.workers.dev"}'
```

## 🚀 Usage

### Manual Operations

```bash
# Fetch Reddit posts
cd scripts
uv run entrypoints/run_daily_fetch

# Process content with LLM
uv run entrypoints/process_content

# Test single operations
uv run src/reddit_fetcher
uv run src/content_processor
```

### Production Deployment

The project includes systemd services for production:

1. Copy service files:

```bash
sudo cp scripts/systemd/*.service /etc/systemd/system/
sudo cp scripts/systemd/*.timer /etc/systemd/system/
```

2. Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable reddit-fetcher.timer
sudo systemctl enable content-processor.timer
sudo systemctl start reddit-fetcher.timer
sudo systemctl start content-processor.timer
```

### Telegram Bot Commands

| Command     | Description                      |
| ----------- | -------------------------------- |
| `/start`    | Welcome message and introduction |
| `/digest`   | Get today's AI news digest       |
| `/chat`     | Start AI conversation mode       |
| `/settings` | View your settings and stats     |
| `/clear`    | Clear conversation history       |
| `/help`     | Show available commands          |

## 📊 Monitoring

### Database Monitoring

Monitor key metrics in Supabase:

- Total posts fetched
- Processing success rate
- User engagement
- Error rates

### Scheduling

Default schedule:

- **Reddit Fetch**: Every 2 hours
- **Content Processing**: Every hour
- **Daily Digest**: 9:00 AM UTC
- **Summary Webhook**: 14:00, 07:00, 01:00 UTC

Modify timer files in `scripts/systemd/` to adjust schedule.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Reddit API    │───▶│  Supabase DB │◀───│  Telegram Bot   │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │   Dobby AI   │
                       └──────────────┘
```

### Components

- **Reddit Fetcher** (`scripts/src/reddit_fetcher.py`): Collects posts and comments
- **Content Processor** (`scripts/src/content_processor.py`): LLM processing pipeline
- **Telegram Bot** (`tgbot-ts/src/index.ts`): User interface and digest delivery
- **Database** (`scripts/sql/`): PostgreSQL schema with Supabase

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
cd scripts && uv sync --dev
cd tgbot-ts && pnpm install --include=dev

# Run type checking
cd tgbot-ts && pnpm run cf-typegen

# Run linting
cd scripts && ruff check .
cd tgbot-ts && pnpm run lint  # If available
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [PRAW](https://praw.readthedocs.io/) for Reddit API integration
- [Grammy.js](https://grammy.dev/) for Telegram bot framework
- [Fireworks AI](https://fireworks.ai/) for LLM processing
- [Supabase](https://supabase.com/) for database and backend services
- [Cloudflare Workers](https://workers.cloudflare.com/) for serverless deployment

## 🆘 Troubleshooting

### Common Issues

**Reddit API Rate Limits**

```bash
# Check current rate limit status in logs
tail -f scripts/reddit_fetch.log | grep "rate"
```

**Supabase Connection Issues**

```bash
# Test database connection
cd scripts
uv run python -c "from src.config.config_models import load_config_from_env; _, supabase_config, _ = load_config_from_env(); print('✅ Supabase config loaded successfully')"
```

**Telegram Bot Not Responding**

```bash
# Check webhook status
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

**Processing Failures**

```bash
# Check processing status in database
SELECT processing_status, COUNT(*) FROM reddit_posts GROUP BY processing_status;
```

### Support

For issues and questions:

1. Check the [Issues](../../issues) page
2. Review logs for error messages
3. Verify all environment variables are set
4. Ensure all services are running

---

Built with ❤️ for the AI community
