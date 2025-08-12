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
import { RedditPushService } from './services/reddit-push';

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

		// Initialize services
		const db = new DatabaseService(env.SUPABASE_URL, env.SUPABASE_KEY);
		const digestGenerator = new DigestGenerator(db);
		const chatHandler = new ChatHandler(fireworks, db, env.FIREWORKS_MODEL);

		// Install conversation plugin
		bot.use(conversations());

		// User tracking middleware
		bot.use(async (ctx, next) => {
			if (ctx.from && !ctx.from.is_bot) {
				try {
					await db.trackUserInteraction(ctx.from);
				} catch (error) {
					console.error('Failed to track user interaction:', error);
				}
			}
			await next();
		});

		// Commands
		bot.command('start', async (ctx) => {
			const welcomeMessage =
				`🤖 **Welcome to AI Daily Digest Bot!**\n\n` +
				`I can help you with:\n` +
				`📰 /digest - Get the top AI posts digest\n` +
				`🔥 /top-news - Get high-scoring AI news\n` +
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
				`/digest - Get the top AI posts digest\n` +
				`/top-news - Get high-scoring AI news (250+ score)\n` +
				// `/chat - Start AI conversation mode\n` +
				// `/settings - Configure your preferences\n` +
				// `/clear - Clear conversation history\n` +
				`/help - Show this help message\n\n` +
				`**Usage Tips:**\n` +
				`• Send any message to chat with AI\n` +
				`• Rate limit: 10 messages per minute\n` +
				`• Daily digest: Top 5 posts from 24-48 hours ago\n` +
				`• High-scoring AI news pushed every 2 hours`;

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

		bot.command('top-news', async (ctx) => {
			try {
				await ctx.replyWithChatAction('typing');
				const redditPushService = new RedditPushService(db);

				// Get high-scoring unpushed posts
				const posts = await redditPushService.getHighScoringUnpushedPosts(250, 48);

				if (posts.length === 0) {
					await ctx.reply('📭 No new high-scoring AI news found (score >250 from last 48 hours).', { parse_mode: 'Markdown' });
					return;
				}

				// Send each post to the user
				for (const post of posts) {
					const message = redditPushService.formatPostForTelegram(post);
					await ctx.reply(message, { parse_mode: 'Markdown' });
					// Small delay between posts
					await new Promise((resolve) => setTimeout(resolve, 500));
				}
			} catch (error) {
				console.error('Reddit command error:', error);
				await ctx.reply("Sorry, I couldn't fetch top AI news right now. Please try again later.");
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

	async scheduled(event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
		const scheduledTime = new Date(event.scheduledTime);
		const cron = event.cron;
		console.log(`Scheduled event triggered at: ${scheduledTime.toISOString()}, cron: ${cron}`);

		try {
			// Validate environment variables
			validateEnvironment(env);

			// Initialize bot
			const bot = new Bot(env.BOT_TOKEN, { botInfo: env.BOT_INFO });

			// Initialize services
			const db = new DatabaseService(env.SUPABASE_URL, env.SUPABASE_KEY);

			// Route to appropriate handler based on cron schedule
			if (cron === '0 13 * * *') {
				// Daily digest at 13:00 UTC
				await handleDailyDigest(bot, db);
			} else if (cron === '0 */2 * * *') {
				// Reddit posts every 2 hours
				await handleRedditPush(bot, db);
			} else {
				console.log(`Unknown cron schedule: ${cron}`);
			}
		} catch (error) {
			console.error('Scheduled event error:', error);
		}
	},
} satisfies ExportedHandler<Env>;

// Helper functions for scheduled tasks
async function handleDailyDigest(bot: Bot, db: DatabaseService): Promise<void> {
	console.log('Processing daily digest...');

	const digestGenerator = new DigestGenerator(db);

	// Get all users
	const userIds = await db.getAllUserIds();
	console.log(`Found ${userIds.length} users for scheduled digest`);

	if (userIds.length === 0) {
		console.log('No users found for digest broadcast');
		return;
	}

	// Generate digest
	const digest = await digestGenerator.getTodaysDigest();

	// Send to all users with error handling
	let successCount = 0;
	let errorCount = 0;

	for (const userId of userIds) {
		try {
			await bot.api.sendMessage(userId, digest, { parse_mode: 'Markdown' });
			successCount++;
			// Add small delay to avoid rate limits
			await new Promise((resolve) => setTimeout(resolve, 100));
		} catch (error: any) {
			console.error(`Failed to send digest to user ${userId}:`, error);

			// Handle bot blocked by user
			if (
				error?.error_code === 403 &&
				(error?.description?.includes('bot was blocked') ||
					error?.description?.includes('user is deactivated') ||
					error?.description?.includes('chat not found'))
			) {
				try {
					await db.markUserBlocked(userId);
					console.log(`Marked user ${userId} as blocked/deleted`);
				} catch (dbError) {
					console.error(`Failed to mark user ${userId} as blocked:`, dbError);
				}
			}

			errorCount++;
		}
	}

	console.log(`Daily digest completed: ${successCount} sent, ${errorCount} failed`);
}

async function handleRedditPush(bot: Bot, db: DatabaseService): Promise<void> {
	console.log('Processing Reddit push...');

	const redditPushService = new RedditPushService(db);

	// Get high-scoring unpushed posts
	const posts = await redditPushService.getHighScoringUnpushedPosts(250, 48);
	console.log(`Found ${posts.length} high-scoring posts to push`);

	if (posts.length === 0) {
		console.log('No high-scoring posts to push');
		return;
	}

	// Get all active users
	const userIds = await db.getAllUserIds();
	console.log(`Found ${userIds.length} users for Reddit push`);

	if (userIds.length === 0) {
		console.log('No users found for Reddit push');
		return;
	}

	// Send each post to all users
	for (const post of posts) {
		const message = redditPushService.formatPostForTelegram(post);
		let successCount = 0;
		let errorCount = 0;

		for (const userId of userIds) {
			try {
				await bot.api.sendMessage(userId, message, { parse_mode: 'Markdown' });
				successCount++;
				// Add delay to avoid rate limits
				await new Promise((resolve) => setTimeout(resolve, 150));
			} catch (error: any) {
				console.error(`Failed to send Reddit post ${post.reddit_id} to user ${userId}:`, error);

				// Handle bot blocked by user
				if (
					error?.error_code === 403 &&
					(error?.description?.includes('bot was blocked') ||
						error?.description?.includes('user is deactivated') ||
						error?.description?.includes('chat not found'))
				) {
					try {
						await db.markUserBlocked(userId);
						console.log(`Marked user ${userId} as blocked/deleted`);
					} catch (dbError) {
						console.error(`Failed to mark user ${userId} as blocked:`, dbError);
					}
				}

				errorCount++;
			}
		}

		// Mark post as pushed regardless of send success
		try {
			await redditPushService.markPostAsPushed(post.reddit_id);
			console.log(`Reddit post ${post.reddit_id} pushed: ${successCount} sent, ${errorCount} failed`);
		} catch (dbError) {
			console.error(`Failed to mark post ${post.reddit_id} as pushed:`, dbError);
		}

		// Longer delay between different posts
		await new Promise((resolve) => setTimeout(resolve, 1000));
	}

	console.log(`Reddit push completed: ${posts.length} posts processed`);
}
