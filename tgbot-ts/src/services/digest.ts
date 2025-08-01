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
  async generateDigest(daysBack: number = 1): Promise<string> {
    const categorizedPosts = await this.db.getPostsByCategory(daysBack);
    
    if (Object.keys(categorizedPosts).length === 0) {
      return this.generateEmptyDigest();
    }

    const sections = this.organizeSections(categorizedPosts);
    const totalPosts = Object.values(categorizedPosts).flat().length;

    // Save digest to database
    const today = new Date().toISOString().split('T')[0];
    const categories = sections.map(s => s.category);
    const digestContent = this.formatDigest(sections, totalPosts);
    
    try {
      await this.db.saveDailyDigest(today, digestContent, totalPosts, categories);
    } catch (error) {
      console.error('Failed to save digest to database:', error);
    }

    return digestContent;
  }

  // Get today's digest or generate if not exists
  async getTodaysDigest(): Promise<string> {
    const today = new Date().toISOString().split('T')[0];
    
    try {
      const existingDigest = await this.db.getDigestByDate(today);
      if (existingDigest) {
        return existingDigest.content;
      }
    } catch (error) {
      console.error('Error fetching existing digest:', error);
    }

    // Generate new digest if none exists
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
      'General': '📰'
    };

    const sections: DigestSection[] = [];

    // Sort categories by priority and post count
    const sortedCategories = Object.keys(categorizedPosts).sort((a, b) => {
      const priorityOrder = [
        'AI Research', 'Industry News', 'Product Launches', 
        'Technical Discussion', 'Tools & Resources', 'Funding & Business',
        'Ethics & Society', 'Open Source', 'General'
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
        emoji: categoryEmojis[category] || '📄'
      });
    }

    return sections;
  }

  // Format the complete digest
  private formatDigest(sections: DigestSection[], totalPosts: number): string {
    const date = new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
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
    const title = this.truncateText(post.title, 80);
    const summary = post.summary ? this.truncateText(post.summary, 120) : '';
    
    let formatted = `**${index}. ${title}**\n`;
    
    if (summary) {
      formatted += `   ${summary}\n`;
    }
    
    formatted += `   👍 ${post.score} | 💬 ${post.num_comments} | r/${post.subreddit}\n`;
    
    if (post.url && post.url !== 'self') {
      formatted += `   🔗 [Read more](${post.url})\n`;
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
      day: 'numeric'
    });

    return `🤖 **AI Daily Digest - ${date}**\n\n` +
           `📊 *No new posts found today*\n\n` +
           `━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
           `🔍 It looks like our AI news sources are quiet today.\n\n` +
           `This could mean:\n` +
           `• Weekend or holiday period\n` +
           `• Technical issues with data collection\n` +
           `• Simply a slow news day in AI\n\n` +
           `💬 *Feel free to ask me about AI topics or check back later!*\n` +
           `🔄 *Next update in ~2 hours*`;
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
        topCategories: []
      };
    } catch (error) {
      console.error('Error getting digest stats:', error);
      return {
        totalDigests: 0,
        avgPostsPerDigest: 0,
        topCategories: []
      };
    }
  }
}