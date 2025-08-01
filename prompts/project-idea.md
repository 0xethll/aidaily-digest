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
