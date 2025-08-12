import { DatabaseService, RedditPost } from './database';

export class RedditPushService {
	private db: DatabaseService;

	constructor(db: DatabaseService) {
		this.db = db;
	}

	// Get high-scoring posts from last 48 hours that haven't been pushed yet
	async getHighScoringUnpushedPosts(minScore: number = 250, hoursBack: number = 48): Promise<RedditPost[]> {
		const now = new Date();
		const cutoffTime = new Date(now.getTime() - hoursBack * 60 * 60 * 1000);

		const { data, error } = await this.db['supabase']
			.from('reddit_posts')
			.select('*')
			.eq('content_type', 'news')
			.gte('created_utc', cutoffTime.toISOString())
			.gte('score', minScore)
			.eq('is_pushed', false) // Only unpushed posts
			.not('summary', 'is', null) // Must have summary
			.order('score', { ascending: false })
			.limit(5);

		if (error) {
			throw new Error(`Failed to get high-scoring posts: ${error.message}`);
		}

		return data || [];
	}

	// Mark a post as pushed
	async markPostAsPushed(redditId: string): Promise<void> {
		const { error } = await this.db['supabase'].from('reddit_posts').update({ is_pushed: true }).eq('reddit_id', redditId);

		if (error) {
			throw new Error(`Failed to mark post as pushed: ${error.message}`);
		}
	}

	// Format a Reddit post for Telegram
	formatPostForTelegram(post: RedditPost): string {
		const emoji = '📢';
		const redditLink = `[View on Reddit](${post.permalink})`;

		let message = `${emoji} **${post.title}**\n\n`;

		if (post.summary) {
			message += `${post.summary}\n\n`;
		}

		if (post.url && !post.is_self) {
			message += `🔗 **Link:** [External URL](${post.url})\n`;
		}

		message += `📱 ${redditLink}`;

		return message;
	}
}
