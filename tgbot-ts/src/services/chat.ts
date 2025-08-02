import OpenAI from 'openai';
import { DatabaseService } from './database';

export interface ChatMessage {
	role: 'user' | 'assistant' | 'system';
	content: string;
}

// OpenAI compatible message type
interface OpenAIChatMessage {
	role: 'user' | 'assistant' | 'system';
	content: string;
}

export class ChatHandler {
	private fireworks: OpenAI;
	private db: DatabaseService;
	private maxContextLength: number = 20;
	private model: string;

	constructor(fireworks: OpenAI, db: DatabaseService, model: string) {
		this.fireworks = fireworks;
		this.db = db;
		this.model = model;
	}

	// Handle user message and generate AI response
	async handleMessage(userMessage: string, userId: number, userName: string = 'User'): Promise<string> {
		try {
			// Sanitize and validate input
			const sanitizedMessage = this.sanitizeInput(userMessage);
			if (!sanitizedMessage) {
				return 'Please send a valid message.';
			}

			// Get conversation context from database
			const context = await this.db.getConversationContext(userId);

			// Add user message to context
			context.push({ role: 'user' as const, content: sanitizedMessage });

			// Generate AI response
			const response = await this.generateResponse(context, userName);

			// Add AI response to context
			context.push({ role: 'assistant', content: response });

			// Trim context if too long
			const trimmedContext = this.trimContext(context);

			// Save updated context to database
			await this.db.saveConversationContext(userId, trimmedContext);

			return response;
		} catch (error) {
			console.error(`Chat error for user ${userId}:`, error);
			return 'I encountered an error processing your message. Please try again.';
		}
	}

	// Generate AI response using Fireworks AI
	private async generateResponse(context: ChatMessage[], userName: string): Promise<string> {
		const systemPrompt = this.getSystemPrompt(userName);
		const messages: OpenAIChatMessage[] = [
			{ role: 'system', content: systemPrompt },
			...context.slice(-15), // Keep last 15 messages for context
		];

		try {
			const completion = await this.fireworks.chat.completions.create({
				model: this.model,
				messages: messages,
				max_tokens: 1000,
				temperature: 0.7,
				top_p: 0.9,
				stream: false,
			});

			const response = completion.choices[0]?.message?.content;
			if (!response) {
				throw new Error('No response from AI model');
			}

			return this.sanitizeOutput(response);
		} catch (error) {
			console.error('Fireworks AI error:', error);
			throw new Error('Failed to generate AI response');
		}
	}

	// Get system prompt for AI assistant
	private getSystemPrompt(userName: string): string {
		return `You are an AI assistant specialized in artificial intelligence, machine learning, and technology topics. You're part of the AI Daily Digest bot that helps users stay updated with AI news and discuss AI-related topics.

Key guidelines:
- Be helpful, informative, and engaging
- Focus on AI, ML, tech, and related topics
- Provide accurate, up-to-date information when possible
- If unsure about recent events, acknowledge your knowledge limitations
- Keep responses concise but comprehensive (max 800 characters)
- Use markdown formatting when helpful
- Be conversational and friendly
- The user's name is ${userName}

You can discuss:
- AI research and developments
- Machine learning concepts and techniques
- AI tools and frameworks
- Industry news and trends
- Technical explanations
- Career advice in AI/ML
- Ethical considerations in AI
- Startup and business aspects of AI

Stay focused on these topics and provide valuable insights to help users understand and engage with the AI landscape.`;
	}

	// Sanitize user input
	private sanitizeInput(input: string): string {
		if (!input || typeof input !== 'string') {
			return '';
		}

		// Remove potentially harmful content
		const sanitized = input
			.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
			.replace(/javascript:/gi, '') // Remove javascript: URLs
			.replace(/vbscript:/gi, '') // Remove vbscript: URLs
			.replace(/data:text\/html/gi, '') // Remove data URLs
			.trim();

		// Check length limits
		if (sanitized.length > 4000) {
			return sanitized.substring(0, 4000);
		}

		return sanitized;
	}

	// Sanitize AI output
	private sanitizeOutput(output: string): string {
		if (!output || typeof output !== 'string') {
			return 'I apologize, but I encountered an issue generating a response.';
		}

		return output.trim();
	}

	// Trim conversation context to stay within limits
	private trimContext(context: ChatMessage[]): ChatMessage[] {
		if (context.length <= this.maxContextLength) {
			return context;
		}

		// Keep the most recent messages
		return context.slice(-this.maxContextLength);
	}

	// Clear user's conversation context
	async clearContext(userId: number): Promise<void> {
		try {
			await this.db.clearConversationContext(userId);
		} catch (error) {
			console.error(`Error clearing context for user ${userId}:`, error);
			throw error;
		}
	}

	// Get context summary for user
	async getContextSummary(userId: number): Promise<{
		messageCount: number;
		lastActivity: string | null;
	}> {
		try {
			const context = await this.db.getConversationContext(userId);
			return {
				messageCount: context.length,
				lastActivity: context.length > 0 ? 'Recent' : null,
			};
		} catch (error) {
			console.error(`Error getting context summary for user ${userId}:`, error);
			return {
				messageCount: 0,
				lastActivity: null,
			};
		}
	}

	// Generate AI summary of recent posts for digest enhancement
	async generatePostSummary(postTitle: string, postContent: string): Promise<string> {
		try {
			const prompt = `Summarize this AI/tech post in 1-2 concise sentences focusing on the key insights or developments:

Title: ${postTitle}
Content: ${postContent.substring(0, 1000)}

Provide a clear, informative summary that highlights what's important for someone following AI news.`;

			const completion = await this.fireworks.chat.completions.create({
				model: this.model,
				messages: [{ role: 'user', content: prompt }],
				max_tokens: 150,
				temperature: 0.3,
				stream: false,
			});

			const summary = completion.choices[0]?.message?.content;
			return summary ? this.sanitizeOutput(summary) : '';
		} catch (error) {
			console.error('Error generating post summary:', error);
			return '';
		}
	}

	// Categorize posts using AI
	async categorizePost(postTitle: string, postContent: string): Promise<string> {
		try {
			const categories = [
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

			const prompt = `Categorize this AI/tech post into one of these categories: ${categories.join(', ')}

Title: ${postTitle}
Content: ${postContent.substring(0, 500)}

Return only the category name that best fits this post.`;

			const completion = await this.fireworks.chat.completions.create({
				model: this.model,
				messages: [{ role: 'user', content: prompt }],
				max_tokens: 20,
				temperature: 0.1,
				stream: false,
			});

			const category = completion.choices[0]?.message?.content?.trim();

			// Validate that the returned category is in our list
			if (category && categories.includes(category)) {
				return category;
			}

			return 'General';
		} catch (error) {
			console.error('Error categorizing post:', error);
			return 'General';
		}
	}
}
