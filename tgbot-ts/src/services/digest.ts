import { DatabaseService, RedditPost } from './database';

export interface DigestSection {
	category: string;
	posts: RedditPost[];
	emoji: string;
}

export class DigestGenerator {
	private db: DatabaseService;

	constructor(db: DatabaseService) {
		this.db = db;
	}

	// Generate daily digest content
	async generateDigest(): Promise<string> {
		const topPosts = await this.db.getPostsForDailyDigest(5);

		if (topPosts.length === 0) {
			return this.generateEmptyDigest();
		}

		return this.formatSimpleDigest(topPosts);
	}

	// Get latest digest (always generate fresh)
	async getTodaysDigest(): Promise<string> {
		return await this.generateDigest();
	}

	// Organize posts into categorized sections
	private organizeSections(categorizedPosts: Record<string, RedditPost[]>): DigestSection[] {
		const categoryEmojis: Record<string, string> = {
			'AI Research': '🔬',
			'Industry News': '🏢',
			'Product Launches': '🚀',
			'Technical Discussion': '💻',
			'Tools & Resources': '🛠️',
			'Funding & Business': '💰',
			'Ethics & Society': '⚖️',
			'Open Source': '🌐',
			General: '📰',
		};

		const sections: DigestSection[] = [];

		// Sort categories by priority and post count
		const sortedCategories = Object.keys(categorizedPosts).sort((a, b) => {
			const priorityOrder = [
				'AI Research',
				'Industry News',
				'Product Launches',
				'Technical Discussion',
				'Tools & Resources',
				'Funding & Business',
				'Ethics & Society',
				'Open Source',
				'General',
			];

			const aPriority = priorityOrder.indexOf(a);
			const bPriority = priorityOrder.indexOf(b);

			if (aPriority !== -1 && bPriority !== -1) {
				return aPriority - bPriority;
			}

			// If category not in priority list, sort by post count
			return categorizedPosts[b].length - categorizedPosts[a].length;
		});

		for (const category of sortedCategories) {
			const posts = categorizedPosts[category]
				.sort((a, b) => b.score - a.score) // Sort by score descending
				.slice(0, 5); // Limit to top 5 posts per category

			sections.push({
				category,
				posts,
				emoji: categoryEmojis[category] || '📄',
			});
		}

		return sections;
	}

	// Format simple daily digest with top 5 posts
	private formatSimpleDigest(posts: RedditPost[]): string {
		const date = new Date().toLocaleDateString('en-US', {
			weekday: 'long',
			year: 'numeric',
			month: 'long',
			day: 'numeric',
		});

		let digest = `🤖 **AI Daily Digest - ${date}**\n\n`;
		digest += `━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;

		for (let i = 0; i < posts.length; i++) {
			const post = posts[i];
			digest += this.formatPost(post, i + 1);
		}

		digest += `━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;
		digest += `💬 *Send me a message to discuss any of these topics!*`;

		return digest;
	}

	// Format the complete digest (kept for backward compatibility)
	private formatDigest(sections: DigestSection[], totalPosts: number): string {
		const date = new Date().toLocaleDateString('en-US', {
			weekday: 'long',
			year: 'numeric',
			month: 'long',
			day: 'numeric',
		});

		let digest = `🤖 **AI Daily Digest - ${date}**\n\n`;
		digest += `📊 *${totalPosts} posts analyzed from AI communities*\n\n`;
		digest += `━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;

		for (const section of sections) {
			if (section.posts.length === 0) continue;

			digest += `${section.emoji} **${section.category.toUpperCase()}**\n\n`;

			for (let i = 0; i < section.posts.length; i++) {
				const post = section.posts[i];
				digest += this.formatPost(post, i + 1);
			}

			digest += `\n`;
		}

		digest += `━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;
		digest += `💬 *Send me a message to discuss any of these topics!*\n`;
		digest += `🔄 *Next digest in ~2 hours*`;

		return digest;
	}

	// Format individual post
	private formatPost(post: RedditPost, index: number): string {
		// const title = this.truncateText(post.title, 80);
		// const summary = post.summary ? this.truncateText(post.summary, 120) : '';
		const contentType = post.content_type || 'General';

		let formatted = `📂 ${contentType}\n`;
		formatted += `**${index}. ${post.summary}**\n`;

		// if (summary) {
		// 	formatted += `   ${summary}\n`;
		// }

		if (post.permalink && post.permalink !== 'self') {
			formatted += `   🔗 [Read more](${post.permalink})\n`;
		}

		formatted += `\n`;

		return formatted;
	}

	// Generate empty digest when no posts available
	private generateEmptyDigest(): string {
		const date = new Date().toLocaleDateString('en-US', {
			weekday: 'long',
			year: 'numeric',
			month: 'long',
			day: 'numeric',
		});

		return (
			`🤖 **AI Daily Digest - ${date}**\n\n` +
			`📊 *No high-scoring posts from 24-48 hours ago*\n\n` +
			`━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
			`🔍 It looks like our AI news sources are quiet.\n\n` +
			`This could mean:\n` +
			`• Weekend or holiday period\n` +
			`• Posts haven't had enough time to gain traction\n` +
			`• Simply a slow news period in AI\n\n` +
			`💬 *Feel free to ask me about AI topics or check back tomorrow!*\n` +
			`🔄 *Next digest tomorrow at 9 AM*`
		);
	}

	// Utility function to truncate text
	private truncateText(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.substring(0, maxLength - 3) + '...';
	}

	// Get digest statistics
	async getDigestStats(): Promise<{
		totalDigests: number;
		avgPostsPerDigest: number;
		topCategories: string[];
	}> {
		try {
			// This would require additional database queries
			// For now, return placeholder stats
			return {
				totalDigests: 0,
				avgPostsPerDigest: 0,
				topCategories: [],
			};
		} catch (error) {
			console.error('Error getting digest stats:', error);
			return {
				totalDigests: 0,
				avgPostsPerDigest: 0,
				topCategories: [],
			};
		}
	}
}
