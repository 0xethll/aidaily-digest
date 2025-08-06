import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { ChatMessage } from './chat';

export interface RedditPost {
	reddit_id: string;
	subreddit_name: string;
	title: string;
	content: string;
	url: string;
	score: number;
	num_comments: number;
	upvote_ratio: number;
	author: string;
	created_utc: string; // Changed to string to match TIMESTAMP WITH TIME ZONE
	is_stickied: boolean;
	is_nsfw: boolean;
	is_self: boolean;
	permalink: string;
	thumbnail: string;
	summary?: string;
	summary_generated_at?: string;
	content_type?: string;
	keywords?: string[];
	content_processed_at?: string;
	processing_status: string;
	url_fetch_attempts: number;
	fetched_at: string;
	created_at: string;
	updated_at: string;
}

export interface DailyDigest {
	id: string; // UUID in the schema
	date: string; // Changed from digest_date to date
	post_count: number; // Changed from total_posts to post_count
	summary: string; // Changed from content to summary
	status: string;
	telegram_message_id?: number;
	created_at: string;
	updated_at: string;
}

export interface DigestPost {
	digest_id: string; // UUID
	post_reddit_id: string; // Changed from post_id to post_reddit_id
}

export interface Subreddit {
	name: string;
	display_name: string;
	description?: string;
	subscribers?: number;
	active_users?: number;
	created_at: string;
	updated_at: string;
}

export interface BotUser {
	user_id: number;
	username?: string;
	first_name?: string;
	last_name?: string;
	language_code?: string;
	is_bot: boolean;
	is_premium?: boolean;
	status: 'active' | 'blocked' | 'deleted';
	first_interaction_at: string;
	last_interaction_at: string;
	interaction_count: number;
	created_at: string;
	updated_at: string;
}

export class DatabaseService {
	private supabase: SupabaseClient;

	constructor(url: string, key: string) {
		this.supabase = createClient(url, key);
	}

	// Get posts from 24-48 hours ago for daily digest
	async getPostsForDailyDigest(limit: number = 5, minSummaryLength: number = 50): Promise<RedditPost[]> {
		const now = new Date();
		const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
		const fortyEightHoursAgo = new Date(now.getTime() - 48 * 60 * 60 * 1000);

		const { data, error } = await this.supabase
			.from('reddit_posts')
			.select('*')
			.gte('created_utc', fortyEightHoursAgo.toISOString())
			.lte('created_utc', twentyFourHoursAgo.toISOString())
			.not('summary', 'is', null)
			.order('score', { ascending: false })
			.limit(limit * 3); // Get more posts to filter from

		if (error) {
			throw new Error(`Database error: ${error.message}`);
		}

		// Additional client-side filtering to ensure summary length
		const filteredPosts = (data || []).filter(post => 
			post.summary && 
			post.summary.trim().length >= minSummaryLength
		);

		return filteredPosts.slice(0, limit);
	}

	// Get recent posts for digest generation (kept for backward compatibility)
	async getRecentPosts(daysBack: number = 1, limit: number = 100): Promise<RedditPost[]> {
		// Validate and clamp input parameters
		const safeDaysBack = Math.max(1, Math.min(30, daysBack));
		const safeLimit = Math.max(1, Math.min(1000, limit));

		const cutoffDate = new Date();
		cutoffDate.setDate(cutoffDate.getDate() - safeDaysBack);

		const { data, error } = await this.supabase
			.from('reddit_posts')
			.select('*')
			.gte('created_utc', cutoffDate.toISOString())
			.order('score', { ascending: false })
			.limit(safeLimit);

		if (error) {
			throw new Error(`Database error: ${error.message}`);
		}

		return data || [];
	}

	// Get posts by category for digest formatting
	async getPostsByCategory(daysBack: number = 1): Promise<Record<string, RedditPost[]>> {
		const posts = await this.getRecentPosts(daysBack);
		const categorized: Record<string, RedditPost[]> = {};

		for (const post of posts) {
			const category = post.content_type || 'General';
			if (!categorized[category]) {
				categorized[category] = [];
			}
			categorized[category].push(post);
		}

		return categorized;
	}

	// Save daily digest
	async saveDailyDigest(digestDate: string, summary: string, postCount: number): Promise<DailyDigest> {
		const { data, error } = await this.supabase
			.from('daily_digests')
			.insert({
				date: digestDate,
				summary,
				post_count: postCount,
				status: 'completed',
			})
			.select()
			.single();

		if (error) {
			throw new Error(`Failed to save digest: ${error.message}`);
		}

		return data;
	}

	// Get latest digest
	async getLatestDigest(): Promise<DailyDigest | null> {
		const { data, error } = await this.supabase.from('daily_digests').select('*').order('date', { ascending: false }).limit(1).single();

		if (error && error.code !== 'PGRST116') {
			// PGRST116 = no rows returned
			throw new Error(`Failed to get latest digest: ${error.message}`);
		}

		return data || null;
	}

	// Get digest by date
	async getDigestByDate(date: string): Promise<DailyDigest | null> {
		console.log(date);
		const { data, error } = await this.supabase.from('daily_digests').select('*').eq('date', date).single();

		if (error && error.code !== 'PGRST116') {
			throw new Error(`Failed to get digest: ${error.message}`);
		}

		return data || null;
	}

	// Save conversation context
	async saveConversationContext(userId: number, context: Array<{ role: string; content: string }>): Promise<void> {
		const { error } = await this.supabase.from('user_conversations').upsert({
			user_id: userId,
			context: JSON.stringify(context),
			updated_at: new Date().toISOString(),
		});

		if (error) {
			throw new Error(`Failed to save conversation: ${error.message}`);
		}
	}

	// Get conversation context
	async getConversationContext(userId: number): Promise<Array<ChatMessage>> {
		const { data, error } = await this.supabase.from('user_conversations').select('context').eq('user_id', userId).single();

		if (error && error.code !== 'PGRST116') {
			throw new Error(`Failed to get conversation: ${error.message}`);
		}

		if (!data?.context) {
			return [];
		}

		try {
			const parsed = JSON.parse(data.context);
			// Validate that parsed data is an array with expected structure
			if (!Array.isArray(parsed)) {
				console.warn(`Invalid conversation context format for user ${userId}: not an array`);
				return [];
			}

			// Validate each message has required properties
			const isValidContext = parsed.every(
				(msg) => msg && typeof msg === 'object' && typeof msg.role === 'string' && typeof msg.content === 'string'
			);

			if (!isValidContext) {
				console.warn(`Invalid conversation context format for user ${userId}: invalid message structure`);
				return [];
			}

			return parsed;
		} catch (parseError) {
			console.error(`Failed to parse conversation context for user ${userId}:`, parseError);
			// Clear corrupted data
			await this.clearConversationContext(userId).catch((clearError) => {
				console.error(`Failed to clear corrupted context for user ${userId}:`, clearError);
			});
			return [];
		}
	}

	// Clear conversation context
	async clearConversationContext(userId: number): Promise<void> {
		const { error } = await this.supabase.from('user_conversations').delete().eq('user_id', userId);

		if (error) {
			throw new Error(`Failed to clear conversation: ${error.message}`);
		}
	}

	// Check if user is admin
	async isUserAdmin(userId: number, adminChatIds: string): Promise<boolean> {
		if (!adminChatIds) return false;

		const adminIds = adminChatIds.split(',').map((id) => parseInt(id.trim()));
		return adminIds.includes(userId);
	}

	// Log security events
	async logSecurityEvent(userId: number, eventType: string, details: Record<string, any>): Promise<void> {
		const { error } = await this.supabase.from('security_logs').insert({
			user_id: userId,
			event_type: eventType,
			details: JSON.stringify(details),
			timestamp: new Date().toISOString(),
		});

		if (error) {
			console.error(`Failed to log security event: ${error.message}`);
		}
	}

	// Get posts by processing status
	async getPostsByProcessingStatus(status: string, limit: number = 50): Promise<RedditPost[]> {
		const { data, error } = await this.supabase
			.from('reddit_posts')
			.select('*')
			.eq('processing_status', status)
			.order('created_utc', { ascending: false })
			.limit(limit);

		if (error) {
			throw new Error(`Failed to get posts by status: ${error.message}`);
		}

		return data || [];
	}

	// Update post processing status
	async updatePostProcessingStatus(redditId: string, status: string, summary?: string): Promise<void> {
		const updateData: any = {
			processing_status: status,
			content_processed_at: new Date().toISOString(),
		};

		if (summary) {
			updateData.summary = summary;
			updateData.summary_generated_at = new Date().toISOString();
		}

		const { error } = await this.supabase.from('reddit_posts').update(updateData).eq('reddit_id', redditId);

		if (error) {
			throw new Error(`Failed to update post status: ${error.message}`);
		}
	}

	// Add posts to digest
	async addPostsToDigest(digestId: string, postRedditIds: string[]): Promise<void> {
		const digestPosts = postRedditIds.map((postId) => ({
			digest_id: digestId,
			post_reddit_id: postId,
		}));

		const { error } = await this.supabase.from('digest_posts').insert(digestPosts);

		if (error) {
			throw new Error(`Failed to add posts to digest: ${error.message}`);
		}
	}

	// Get subreddits
	async getSubreddits(): Promise<Subreddit[]> {
		const { data, error } = await this.supabase.from('subreddits').select('*').order('name');

		if (error) {
			throw new Error(`Failed to get subreddits: ${error.message}`);
		}

		return data || [];
	}

	// Track user interaction
	async trackUserInteraction(user: {
		id: number;
		username?: string;
		first_name?: string;
		last_name?: string;
		language_code?: string;
		is_bot: boolean;
		is_premium?: boolean;
	}): Promise<void> {
		const now = new Date().toISOString();
		
		const { error } = await this.supabase
			.from('bot_users')
			.upsert({
				user_id: user.id,
				username: user.username,
				first_name: user.first_name,
				last_name: user.last_name,
				language_code: user.language_code,
				is_bot: user.is_bot,
				is_premium: user.is_premium,
				status: 'active',
				last_interaction_at: now,
				updated_at: now
			}, {
				onConflict: 'user_id'
			});

		if (error) {
			throw new Error(`Failed to track user interaction: ${error.message}`);
		}

		// Increment interaction count
		const { error: incrementError } = await this.supabase
			.rpc('increment_user_interaction', { p_user_id: user.id });

		if (incrementError) {
			console.error('Failed to increment interaction count:', incrementError);
		}
	}

	// Mark user as blocked
	async markUserBlocked(userId: number): Promise<void> {
		const { error } = await this.supabase
			.from('bot_users')
			.update({
				status: 'blocked',
				updated_at: new Date().toISOString()
			})
			.eq('user_id', userId);

		if (error) {
			throw new Error(`Failed to mark user blocked: ${error.message}`);
		}
	}

	// Get all active user IDs for broadcast
	async getAllUserIds(): Promise<number[]> {
		const { data, error } = await this.supabase
			.from('bot_users')
			.select('user_id')
			.eq('status', 'active')
			.order('last_interaction_at', { ascending: false });

		if (error) {
			throw new Error(`Failed to get users: ${error.message}`);
		}

		return (data || []).map(row => row.user_id);
	}

	// Get user statistics
	async getUserStats(): Promise<{ total: number; active: number; blocked: number }> {
		const { data, error } = await this.supabase
			.from('bot_users')
			.select('status')
			.not('status', 'eq', 'deleted');

		if (error) {
			throw new Error(`Failed to get user stats: ${error.message}`);
		}

		const stats = (data || []).reduce((acc, row) => {
			acc.total++;
			acc[row.status as 'active' | 'blocked']++;
			return acc;
		}, { total: 0, active: 0, blocked: 0 });

		return stats;
	}
}
