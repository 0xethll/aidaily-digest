import { createClient, SupabaseClient } from '@supabase/supabase-js';

export interface RedditPost {
  id: string;
  title: string;
  content: string;
  url: string;
  score: number;
  subreddit: string;
  author: string;
  created_utc: number;
  upvote_ratio: number;
  num_comments: number;
  summary?: string;
  category?: string;
  sentiment?: number;
  keywords?: string[];
  fetched_at: string;
}

export interface DailyDigest {
  id: number;
  digest_date: string;
  content: string;
  total_posts: number;
  categories: string[];
  created_at: string;
}

export interface DigestPost {
  id: number;
  digest_id: number;
  post_id: string;
  category: string;
  position: number;
}

export class DatabaseService {
  private supabase: SupabaseClient;

  constructor(url: string, key: string) {
    this.supabase = createClient(url, key);
  }

  // Get recent posts for digest generation
  async getRecentPosts(daysBack: number = 1, limit: number = 100): Promise<RedditPost[]> {
    // Validate and clamp input parameters
    const safeDaysBack = Math.max(1, Math.min(30, daysBack));
    const safeLimit = Math.max(1, Math.min(1000, limit));
    
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - safeDaysBack);
    
    const { data, error } = await this.supabase
      .from('reddit_posts')
      .select('*')
      .gte('created_utc', Math.floor(cutoffDate.getTime() / 1000))
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
      const category = post.category || 'General';
      if (!categorized[category]) {
        categorized[category] = [];
      }
      categorized[category].push(post);
    }

    return categorized;
  }

  // Save daily digest
  async saveDailyDigest(
    digestDate: string,
    content: string,
    totalPosts: number,
    categories: string[]
  ): Promise<DailyDigest> {
    const { data, error } = await this.supabase
      .from('daily_digests')
      .insert({
        digest_date: digestDate,
        content,
        total_posts: totalPosts,
        categories
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
    const { data, error } = await this.supabase
      .from('daily_digests')
      .select('*')
      .order('digest_date', { ascending: false })
      .limit(1)
      .single();

    if (error && error.code !== 'PGRST116') { // PGRST116 = no rows returned
      throw new Error(`Failed to get latest digest: ${error.message}`);
    }

    return data || null;
  }

  // Get digest by date
  async getDigestByDate(date: string): Promise<DailyDigest | null> {
    const { data, error } = await this.supabase
      .from('daily_digests')
      .select('*')
      .eq('digest_date', date)
      .single();

    if (error && error.code !== 'PGRST116') {
      throw new Error(`Failed to get digest: ${error.message}`);
    }

    return data || null;
  }

  // Save conversation context
  async saveConversationContext(
    userId: number,
    context: Array<{ role: string; content: string }>
  ): Promise<void> {
    const { error } = await this.supabase
      .from('user_conversations')
      .upsert({
        user_id: userId,
        context: JSON.stringify(context),
        updated_at: new Date().toISOString()
      });

    if (error) {
      throw new Error(`Failed to save conversation: ${error.message}`);
    }
  }

  // Get conversation context
  async getConversationContext(userId: number): Promise<Array<{ role: string; content: string }>> {
    const { data, error } = await this.supabase
      .from('user_conversations')
      .select('context')
      .eq('user_id', userId)
      .single();

    if (error && error.code !== 'PGRST116') {
      throw new Error(`Failed to get conversation: ${error.message}`);
    }

    if (!data?.context) {
      return [];
    }

    try {
      return JSON.parse(data.context);
    } catch {
      return [];
    }
  }

  // Clear conversation context
  async clearConversationContext(userId: number): Promise<void> {
    const { error } = await this.supabase
      .from('user_conversations')
      .delete()
      .eq('user_id', userId);

    if (error) {
      throw new Error(`Failed to clear conversation: ${error.message}`);
    }
  }

  // Check if user is admin
  async isUserAdmin(userId: number, adminChatIds: string): Promise<boolean> {
    if (!adminChatIds) return false;
    
    const adminIds = adminChatIds.split(',').map(id => parseInt(id.trim()));
    return adminIds.includes(userId);
  }

  // Log security events
  async logSecurityEvent(
    userId: number,
    eventType: string,
    details: Record<string, any>
  ): Promise<void> {
    const { error } = await this.supabase
      .from('security_logs')
      .insert({
        user_id: userId,
        event_type: eventType,
        details: JSON.stringify(details),
        timestamp: new Date().toISOString()
      });

    if (error) {
      console.error(`Failed to log security event: ${error.message}`);
    }
  }
}