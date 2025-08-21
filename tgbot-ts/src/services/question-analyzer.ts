import OpenAI from 'openai';
import { DatabaseService, RedditPost } from './database';

interface AnalysisResult {
	keywords: string[];
	intent: 'general_question' | 'specific_topic' | 'recent_news' | 'comparison' | 'tutorial' | 'explanation' | 'other';
	topicAreas: string[];
	timeframe?: 'recent' | 'week' | 'month' | 'any';
}

interface RelevantContent {
	posts: RedditPost[];
	totalTokens: number;
	truncated: boolean;
}

export class QuestionAnalyzer {
	private fireworks: OpenAI;
	private db: DatabaseService;
	private model: string;
	private maxTokens: number = 100000; // Reserve ~28k tokens for response generation

	constructor(fireworks: OpenAI, db: DatabaseService, model: string) {
		this.fireworks = fireworks;
		this.db = db;
		this.model = model;
	}

	// Main function to analyze user question and retrieve relevant content
	async analyzeAndRetrieve(userMessage: string, userId: number): Promise<{
		analysis: AnalysisResult;
		relevantContent: RelevantContent;
		searchQuery: string;
	}> {
		try {
			// Step 1: Analyze the user's question
			const analysis = await this.analyzeUserQuestion(userMessage);

			// Step 2: Generate search strategy
			const searchQuery = this.generateSearchQuery(analysis, userMessage);

			// Step 3: Retrieve relevant posts
			const relevantContent = await this.retrieveRelevantPosts(analysis, searchQuery);

			return {
				analysis,
				relevantContent,
				searchQuery
			};
		} catch (error) {
			console.error('Error in analyzeAndRetrieve:', error);
			// Return fallback analysis
			return {
				analysis: {
					keywords: this.extractBasicKeywords(userMessage),
					intent: 'general_question',
					topicAreas: ['AI'],
					timeframe: 'recent'
				},
				relevantContent: {
					posts: [],
					totalTokens: 0,
					truncated: false
				},
				searchQuery: userMessage
			};
		}
	}

	// Analyze user question using AI
	private async analyzeUserQuestion(userMessage: string): Promise<AnalysisResult> {
		const prompt = `Analyze this user question about AI/technology and extract:

User Question: "${userMessage}"

Please return a JSON object with:
1. keywords: Array of 3-5 relevant search keywords/phrases
2. intent: One of [general_question, specific_topic, recent_news, comparison, tutorial, explanation, other]
3. topicAreas: Array of relevant topic areas (e.g., "machine learning", "LLMs", "computer vision", "robotics", "startups", etc.)
4. timeframe: One of [recent, week, month, any] based on if they want current/recent info

Focus on AI, machine learning, technology, and related topics.

Return only the JSON object, no other text.`;

		try {
			const completion = await this.fireworks.chat.completions.create({
				model: this.model,
				messages: [{ role: 'user', content: prompt }],
				max_tokens: 300,
				temperature: 0.1,
				stream: false,
			});

			const response = completion.choices[0]?.message?.content?.trim();
			if (!response) {
				throw new Error('No response from AI model');
			}

			// Parse JSON response
			const analysis = JSON.parse(response) as AnalysisResult;
			
			// Validate the response structure
			if (!analysis.keywords || !Array.isArray(analysis.keywords)) {
				throw new Error('Invalid analysis format: missing keywords array');
			}

			return analysis;
		} catch (error) {
			console.error('Error analyzing user question:', error);
			// Fallback to basic keyword extraction
			return {
				keywords: this.extractBasicKeywords(userMessage),
				intent: 'general_question',
				topicAreas: ['AI'],
				timeframe: 'recent'
			};
		}
	}

	// Generate search query based on analysis
	private generateSearchQuery(analysis: AnalysisResult, originalMessage: string): string {
		// Combine keywords and topic areas for search
		const searchTerms = [
			...analysis.keywords,
			...analysis.topicAreas
		].filter((term, index, arr) => arr.indexOf(term) === index); // Remove duplicates

		return searchTerms.join(' ');
	}

	// Retrieve relevant posts based on analysis
	private async retrieveRelevantPosts(analysis: AnalysisResult, searchQuery: string): Promise<RelevantContent> {
		try {
			// Determine date range based on timeframe
			const daysBack = this.getTimeframeDays(analysis.timeframe);

			// Search in multiple ways and combine results
			const [
				keywordPosts,
				titlePosts,
				summaryPosts,
				recentTopPosts
			] = await Promise.all([
				this.searchPostsByKeywords(analysis.keywords, daysBack),
				this.searchPostsByTitle(searchQuery, daysBack),
				this.searchPostsBySummary(searchQuery, daysBack),
				this.getRecentTopPosts(daysBack, 20)
			]);

			// Combine and deduplicate posts
			const allPosts = this.deduplicatePosts([
				...keywordPosts,
				...titlePosts,
				...summaryPosts,
				...recentTopPosts
			]);

			// Score and rank posts by relevance
			const scoredPosts = this.scorePostRelevance(allPosts, analysis, searchQuery);

			// Manage token limit
			return this.managePosts(scoredPosts);
		} catch (error) {
			console.error('Error retrieving relevant posts:', error);
			return {
				posts: [],
				totalTokens: 0,
				truncated: false
			};
		}
	}

	// Search posts by keywords in content
	private async searchPostsByKeywords(keywords: string[], daysBack: number): Promise<RedditPost[]> {
		if (keywords.length === 0) return [];

		try {
			return await this.db.searchPostsByKeywords(keywords, daysBack, 50);
		} catch (error) {
			console.error('Error searching posts by keywords:', error);
			return [];
		}
	}

	// Search posts by title
	private async searchPostsByTitle(searchQuery: string, daysBack: number): Promise<RedditPost[]> {
		try {
			return await this.db.searchPostsByTitle(searchQuery, daysBack, 30);
		} catch (error) {
			console.error('Error searching posts by title:', error);
			return [];
		}
	}

	// Search posts by summary
	private async searchPostsBySummary(searchQuery: string, daysBack: number): Promise<RedditPost[]> {
		try {
			return await this.db.searchPostsBySummary(searchQuery, daysBack, 30);
		} catch (error) {
			console.error('Error searching posts by summary:', error);
			return [];
		}
	}

	// Get recent top posts as fallback
	private async getRecentTopPosts(daysBack: number, limit: number): Promise<RedditPost[]> {
		return await this.db.getRecentPosts(daysBack, limit);
	}

	// Remove duplicate posts
	private deduplicatePosts(posts: RedditPost[]): RedditPost[] {
		const seen = new Set<string>();
		return posts.filter(post => {
			if (seen.has(post.reddit_id)) {
				return false;
			}
			seen.add(post.reddit_id);
			return true;
		});
	}

	// Score posts by relevance to the user's question
	private scorePostRelevance(posts: RedditPost[], analysis: AnalysisResult, searchQuery: string): RedditPost[] {
		const keywords = analysis.keywords.map(k => k.toLowerCase());
		const topicAreas = analysis.topicAreas.map(t => t.toLowerCase());
		const searchTerms = searchQuery.toLowerCase().split(' ');

		return posts
			.map(post => {
				let score = post.score; // Start with Reddit score

				// Title matching
				const titleLower = post.title.toLowerCase();
				const titleScore = keywords.reduce((acc, keyword) => {
					return acc + (titleLower.includes(keyword) ? 100 : 0);
				}, 0);

				// Content matching
				const contentLower = (post.content || '').toLowerCase();
				const contentScore = keywords.reduce((acc, keyword) => {
					return acc + (contentLower.includes(keyword) ? 50 : 0);
				}, 0);

				// Summary matching
				const summaryLower = (post.summary || '').toLowerCase();
				const summaryScore = keywords.reduce((acc, keyword) => {
					return acc + (summaryLower.includes(keyword) ? 75 : 0);
				}, 0);

				// Topic area matching
				const topicScore = topicAreas.reduce((acc, topic) => {
					const text = `${titleLower} ${contentLower} ${summaryLower}`;
					return acc + (text.includes(topic) ? 80 : 0);
				}, 0);

				// Recency bonus (more recent posts get higher scores)
				const postDate = new Date(post.created_utc);
				const daysOld = (Date.now() - postDate.getTime()) / (1000 * 60 * 60 * 24);
				const recencyScore = Math.max(0, 50 - daysOld * 2);

				const totalScore = score + titleScore + contentScore + summaryScore + topicScore + recencyScore;

				return { ...post, relevanceScore: totalScore };
			})
			.sort((a, b) => b.relevanceScore - a.relevanceScore)
			.map(({ relevanceScore, ...post }) => post); // Remove the score field
	}

	// Manage posts to fit within token limit
	private managePosts(posts: RedditPost[]): RelevantContent {
		let totalTokens = 0;
		const selectedPosts: RedditPost[] = [];
		let truncated = false;

		for (const post of posts) {
			// Estimate tokens for this post (rough estimate: 1 token ≈ 4 characters)
			const postText = `${post.title} ${post.content || ''} ${post.summary || ''}`;
			const estimatedTokens = Math.ceil(postText.length / 4);

			if (totalTokens + estimatedTokens > this.maxTokens) {
				truncated = true;
				break;
			}

			selectedPosts.push(post);
			totalTokens += estimatedTokens;

			// Limit to reasonable number of posts
			if (selectedPosts.length >= 50) {
				truncated = true;
				break;
			}
		}

		return {
			posts: selectedPosts,
			totalTokens,
			truncated
		};
	}

	// Get timeframe in days
	private getTimeframeDays(timeframe?: string): number {
		switch (timeframe) {
			case 'recent':
				return 3;
			case 'week':
				return 7;
			case 'month':
				return 30;
			case 'any':
			default:
				return 14; // Default to 2 weeks
		}
	}

	// Basic keyword extraction fallback
	private extractBasicKeywords(text: string): string[] {
		// Remove common words and extract meaningful terms
		const commonWords = new Set(['the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by', 'what', 'how', 'when', 'where', 'why', 'who']);
		
		const words = text
			.toLowerCase()
			.replace(/[^\w\s]/g, ' ')
			.split(/\s+/)
			.filter(word => word.length > 2 && !commonWords.has(word))
			.slice(0, 5);

		return words.length > 0 ? words : ['AI', 'technology'];
	}

	// Format posts for AI context
	formatPostsForContext(posts: RedditPost[]): string {
		if (posts.length === 0) {
			return "No relevant posts found in the database.";
		}

		return posts.map((post, index) => {
			const content = post.summary || post.content || 'No content available';
			return `Post ${index + 1}:
Title: ${post.title}
Subreddit: r/${post.subreddit_name}
Score: ${post.score}
Summary: ${content.substring(0, 500)}${content.length > 500 ? '...' : ''}
URL: https://reddit.com${post.permalink}
---`;
		}).join('\n');
	}
}