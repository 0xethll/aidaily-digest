import { Bot, Context, webhookCallback } from 'grammy';
import { conversations, createConversation, type ConversationFlavor } from '@grammyjs/conversations';
import { Menu } from '@grammyjs/menu';
import { limit } from '@grammyjs/ratelimiter';
import { UserFromGetMe } from 'grammy/types';
import { createClient } from '@supabase/supabase-js';
import OpenAI from 'openai';
import { DatabaseService } from './services/database';
import { DigestGenerator } from './services/digest';
import { ChatHandler } from './services/chat';

export interface Env {
	BOT_INFO: UserFromGetMe;
	BOT_TOKEN: string;
	SUPABASE_URL: string;
	SUPABASE_KEY: string;
	FIREWORKS_API_KEY: string;
	TELEGRAM_ADMIN_CHAT_IDS?: string;
	FIREWORKS_MODEL: string;
}

type MyContext = Context & { conversation: any };

function validateEnvironment(env: Env): void {
	const requiredVars = ['BOT_TOKEN', 'SUPABASE_URL', 'SUPABASE_KEY', 'FIREWORKS_API_KEY', 'FIREWORKS_MODEL'];

	const missing = requiredVars.filter((varName) => !env[varName as keyof Env]);

	if (missing.length > 0) {
		throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
	}
}

async function handleScheduled(env: Env): Promise<void> {
	try {
		// Validate environment variables
		validateEnvironment(env);

		console.log('Running scheduled digest generation...');

		// Initialize services
		const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_KEY);
		const fireworks = new OpenAI({
			apiKey: env.FIREWORKS_API_KEY,
			baseURL: 'https://api.fireworks.ai/inference/v1',
		});

		const db = new DatabaseService(env.SUPABASE_URL, env.SUPABASE_KEY);
		const digestGenerator = new DigestGenerator(db);

		// Generate today's digest
		const digest = await digestGenerator.generateDigest();

		// Optional: Send digest to admin users
		if (env.TELEGRAM_ADMIN_CHAT_IDS) {
			const bot = new Bot(env.BOT_TOKEN, { botInfo: env.BOT_INFO });
			const adminIds = env.TELEGRAM_ADMIN_CHAT_IDS.split(',').map((id) => parseInt(id.trim()));

			for (const adminId of adminIds) {
				try {
					await bot.api.sendMessage(adminId, `📅 **Scheduled Digest Generated**\n\n${digest}`, {
						parse_mode: 'Markdown',
					});
				} catch (error) {
					console.error(`Failed to send digest to admin ${adminId}:`, error);
				}
			}
		}

		console.log('Scheduled digest generation completed');
	} catch (error) {
		console.error('Scheduled digest generation failed:', error);
	}
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		// Validate environment variables
		validateEnvironment(env);

		// Initialize bot with conversation support
		const bot = new Bot<ConversationFlavor<Context>>(env.BOT_TOKEN, { botInfo: env.BOT_INFO });

		// Initialize Supabase client
		const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_KEY);

		// Initialize Fireworks AI client
		const fireworks = new OpenAI({
			apiKey: env.FIREWORKS_API_KEY,
			baseURL: 'https://api.fireworks.ai/inference/v1',
		});

		// Rate limiting middleware
		// bot.use(
		// 	limit({
		// 		timeFrame: 60000, // 1 minute
		// 		limit: 10,
		// 		onLimitExceeded: async (ctx) => {
		// 			await ctx.reply("⚠️ You're sending messages too quickly. Please wait before sending another message.");
		// 		},
		// 	})
		// );

		// Install conversation plugin
		bot.use(conversations());

		// Initialize services
		const db = new DatabaseService(env.SUPABASE_URL, env.SUPABASE_KEY);
		const digestGenerator = new DigestGenerator(db);
		const chatHandler = new ChatHandler(fireworks, db, env.FIREWORKS_MODEL);

		// Commands
		bot.command('start', async (ctx) => {
			const welcomeMessage =
				`🤖 **Welcome to AI Daily Digest Bot!**\n\n` +
				`I can help you with:\n` +
				`📰 /digest - Get the latest AI news digest\n` +
				// `💬 /chat - Start a conversation about AI\n` +
				// `⚙️ /settings - Configure your preferences\n` +
				`❓ /help - Get help and commands\n\n` +
				`Just send me a message to start chatting about AI topics!`;

			await ctx.reply(welcomeMessage, { parse_mode: 'Markdown' });
		});

		bot.command('help', async (ctx) => {
			const helpMessage =
				`🔧 **Available Commands:**\n\n` +
				`/start - Welcome message and introduction\n` +
				`/digest - Get today's AI news digest\n` +
				// `/chat - Start AI conversation mode\n` +
				// `/settings - Configure your preferences\n` +
				// `/clear - Clear conversation history\n` +
				`/help - Show this help message\n\n` +
				`**Usage Tips:**\n` +
				`• Send any message to chat with AI\n` +
				`• Rate limit: 10 messages per minute\n` +
				`• Daily digest: Top 5 posts from 24-48 hours ago\n` +
				`• Generated daily at 9 AM`;

			await ctx.reply(helpMessage, { parse_mode: 'Markdown' });
		});

		bot.command('digest', async (ctx) => {
			try {
				await ctx.replyWithChatAction('typing');
				const digest = await digestGenerator.getTodaysDigest();
				await ctx.reply(digest, { parse_mode: 'Markdown' });
			} catch (error) {
				console.error('Digest error:', error);
				await ctx.reply("Sorry, I couldn't generate the digest right now. Please try again later.");
			}
		});

		bot.command('chat', async (ctx) => {
			const chatMessage =
				`💬 **Chat Mode Activated**\n\n` +
				`I'm ready to discuss AI topics with you! You can ask me about:\n\n` +
				`🔬 AI research and developments\n` +
				`💻 Machine learning techniques\n` +
				`🛠️ AI tools and frameworks\n` +
				`📈 Industry trends and news\n` +
				`⚖️ AI ethics and society\n` +
				`💼 Career advice in AI/ML\n\n` +
				`Just send me your question or start a conversation!`;

			await ctx.reply(chatMessage, { parse_mode: 'Markdown' });
		});

		bot.command('clear', async (ctx) => {
			try {
				const userId = ctx.from?.id;
				if (!userId) return;

				await chatHandler.clearContext(userId);
				await ctx.reply('🗑️ Your conversation history has been cleared!');
			} catch (error) {
				console.error('Clear context error:', error);
				await ctx.reply("Sorry, I couldn't clear your conversation history. Please try again.");
			}
		});

		bot.command('settings', async (ctx) => {
			try {
				const userId = ctx.from?.id;
				if (!userId) return;

				const contextSummary = await chatHandler.getContextSummary(userId);
				const isAdmin = await db.isUserAdmin(userId, env.TELEGRAM_ADMIN_CHAT_IDS || '');

				const settingsMessage =
					`⚙️ **Your Settings**\n\n` +
					`👤 User ID: ${userId}\n` +
					`💬 Conversation Messages: ${contextSummary.messageCount}\n` +
					`🔑 Admin Status: ${isAdmin ? 'Yes' : 'No'}\n\n` +
					`**Available Actions:**\n` +
					`/clear - Clear conversation history\n` +
					`/digest - Get latest digest\n` +
					`/help - View all commands`;

				await ctx.reply(settingsMessage, { parse_mode: 'Markdown' });
			} catch (error) {
				console.error('Settings error:', error);
				await ctx.reply("Sorry, I couldn't load your settings. Please try again.");
			}
		});

		// Handle text messages for chat
		bot.on('message:text', async (ctx) => {
			try {
				const userId = ctx.from?.id;
				const userMessage = ctx.message?.text;
				const userName = ctx.from?.first_name || 'User';

				if (!userId || !userMessage) return;

				// Skip if message starts with / (command)
				if (userMessage.startsWith('/')) return;

				await ctx.replyWithChatAction('typing');

				const response = await chatHandler.handleMessage(userMessage, userId, userName);
				await ctx.reply(response, { parse_mode: 'Markdown' });
			} catch (error) {
				console.error('Message handling error:', error);
				await ctx.reply('I encountered an error processing your message. Please try again.');
			}
		});

		// Error handling
		bot.catch((err) => {
			console.error('Bot error:', err);
		});

		// Handle webhook
		return webhookCallback(bot, 'cloudflare-mod')(request);
	},

	async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
		// Handle scheduled events (cron triggers)
		ctx.waitUntil(handleScheduled(env));
	},
} satisfies ExportedHandler<Env>;
