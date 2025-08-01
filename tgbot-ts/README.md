# AI Daily Digest Telegram Bot (Grammy.js + Cloudflare Workers)

A TypeScript Telegram bot built with Grammy.js that provides AI news digests and interactive chat functionality, deployed on Cloudflare Workers.

## Features

- 🤖 **Daily AI Digest**: Automated summaries of AI news from Reddit
- 💬 **AI Chat**: Interactive conversations about AI topics using Fireworks AI
- 🔒 **Security**: Rate limiting, input validation, and secure data handling
- ⚡ **Serverless**: Deployed on Cloudflare Workers for global performance
- 📊 **Database**: Supabase integration for persistent data storage

## Commands

- `/start` - Welcome message and introduction
- `/digest` - Get today's AI news digest
- `/chat` - Start AI conversation mode
- `/settings` - View your settings and stats
- `/clear` - Clear conversation history
- `/help` - Show available commands

## Setup

### Prerequisites

- Node.js 18+
- Cloudflare account
- Supabase account
- Telegram Bot Token
- Fireworks AI API key

### Environment Variables

Set these secrets in Cloudflare Workers:

```bash
BOT_TOKEN=your_telegram_bot_token
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
FIREWORKS_API_KEY=your_fireworks_api_key
TELEGRAM_ADMIN_CHAT_IDS=123456789,987654321  # Optional admin user IDs
```

### Database Setup

1. Run the existing database schema from the main project
2. Run the additional schema for bot-specific tables:

```sql
-- Run database-schema.sql in your Supabase SQL editor
```

### Deployment

1. Install dependencies:
```bash
npm install
```

2. Configure your bot info in `wrangler.jsonc`

3. Set environment secrets:
```bash
npx wrangler secret put BOT_TOKEN
npx wrangler secret put SUPABASE_URL  
npx wrangler secret put SUPABASE_KEY
npx wrangler secret put FIREWORKS_API_KEY
npx wrangler secret put TELEGRAM_ADMIN_CHAT_IDS  # Optional
```

4. Deploy to Cloudflare Workers:
```bash
npm run deploy
```

5. Set up webhook URL with Telegram:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-worker.your-subdomain.workers.dev"}'
```

## Development

```bash
# Start development server
npm run dev

# Run tests
npm test

# Generate TypeScript types for Cloudflare Workers
npm run cf-typegen
```

## Architecture

- **Grammy.js**: Modern Telegram bot framework
- **Cloudflare Workers**: Serverless runtime
- **Supabase**: PostgreSQL database with real-time features
- **Fireworks AI**: LLM for chat functionality
- **TypeScript**: Type-safe development

## Security Features

- ⚡ Rate limiting (10 messages/minute per user)
- 🛡️ Input sanitization and validation
- 🔒 Secure error handling
- 📝 Security event logging
- 🚫 Malicious content filtering

## Performance

- Global edge deployment via Cloudflare
- Automatic conversation context trimming
- Efficient database queries with indexing
- Response caching for digests

## Monitoring

- Cloudflare Workers analytics
- Supabase real-time metrics
- Security event logging
- Rate limiting statistics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if needed
5. Submit a pull request

## License

MIT License - see LICENSE file for details