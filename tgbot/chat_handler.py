"""
Chat handler module for LLM-powered conversations.
Handles user messages and provides AI-powered responses using the same LLM used for content processing.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import openai
from openai import AsyncOpenAI

from config import LLMConfig

logger = logging.getLogger(__name__)


class ChatHandler:
    """Handles LLM-powered chat conversations with users"""
    
    def __init__(self, llm_config: LLMConfig):
        self.config = llm_config
        self.client = AsyncOpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=llm_config.fireworks_api_key,
            timeout=llm_config.timeout
        )
        
        # System prompt for the chat bot
        self.system_prompt = """You are an AI assistant that helps people stay informed about artificial intelligence developments. You have access to curated daily content from AI communities on Reddit including:

- r/artificial - General AI discussions and news
- r/OpenAI - OpenAI-specific content and developments  
- r/ClaudeAI - Anthropic's Claude AI discussions
- r/LocalLLaMA - Local language model developments
- r/LangChain - LangChain framework discussions
- r/AI_Agents - AI agent development and applications
- r/PromptEngineering - Prompt engineering techniques
- r/singularity - AI singularity and futurism discussions

Your role is to:
1. Answer questions about AI developments, trends, and technologies
2. Provide insights about the AI community and discussions
3. Help users understand complex AI concepts
4. Share interesting developments from the AI space
5. Engage in thoughtful conversations about AI's impact and future

Be helpful, knowledgeable, and conversational. Keep responses concise but informative. If you don't know something specific, acknowledge it honestly. Focus on being genuinely helpful rather than just impressive.

You're part of an AI Daily Digest system that curates and summarizes the best AI content from Reddit communities."""
    
    async def handle_message(
        self,
        user_message: str,
        user_id: int,
        user_name: Optional[str] = None,
        chat_context: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Handle a user message and generate an AI response
        
        Args:
            user_message: The user's message text
            user_id: Telegram user ID
            user_name: User's display name (optional)
            chat_context: Previous conversation context (optional)
        
        Returns:
            AI-generated response
        """
        try:
            # Build conversation messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation context if available
            if chat_context:
                messages.extend(chat_context[-10:])  # Keep last 10 messages for context
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            logger.info(f"Processing chat message from user {user_id} ({user_name}): {user_message[:100]}...")
            
            # Generate response
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            ai_response = response.choices[0].message.content
            if not ai_response:
                return "I'm sorry, I couldn't generate a response right now. Please try again."
            
            # Log successful response
            logger.info(f"Generated response for user {user_id}: {len(ai_response)} characters")
            return ai_response.strip()
            
        except openai.RateLimitError:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return "I'm experiencing high demand right now. Please wait a moment and try again."
            
        except openai.APITimeoutError:
            logger.warning(f"API timeout for user {user_id}")
            return "My response took too long to generate. Please try asking again."
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error for user {user_id}: {e}")
            return "I'm having technical difficulties right now. Please try again in a few minutes."
            
        except Exception as e:
            logger.error(f"Unexpected error handling message from user {user_id}: {e}")
            return "Something went wrong while processing your message. Please try again."
    
    async def handle_ai_question(self, question: str) -> str:
        """
        Handle a specific AI-related question with more focused context
        
        Args:
            question: User's AI-related question
        
        Returns:
            AI-generated response
        """
        try:
            focused_prompt = """You are an AI expert assistant specializing in artificial intelligence developments and trends. You're part of a system that monitors AI communities and can provide insights about:

- Latest AI research and breakthroughs
- AI tools and applications
- Machine learning techniques
- AI safety and ethics
- Industry developments and trends
- AI community discussions

Provide accurate, helpful, and insightful answers about AI topics. Be specific when you can, but acknowledge when you're uncertain about recent developments."""
            
            messages = [
                {"role": "system", "content": focused_prompt},
                {"role": "user", "content": question}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature * 0.8,  # Slightly lower temperature for factual questions
                max_tokens=self.config.max_tokens
            )
            
            ai_response = response.choices[0].message.content
            return ai_response.strip() if ai_response else "I couldn't generate a response to that question."
            
        except Exception as e:
            logger.error(f"Error handling AI question: {e}")
            return "I encountered an error while processing your AI question. Please try again."
    
    async def generate_topic_summary(self, topic: str) -> str:
        """
        Generate a summary about a specific AI topic
        
        Args:
            topic: The AI topic to summarize
        
        Returns:
            Topic summary
        """
        try:
            prompt = f"""Provide a concise but informative overview of the following AI topic: {topic}

Include:
- What it is and why it's important
- Current state of development  
- Key players or applications
- Recent trends or developments
- Relevance to the broader AI ecosystem

Keep it accessible but informative, around 200-300 words."""
            
            messages = [
                {"role": "system", "content": "You are an AI expert providing educational summaries about AI topics."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=0.3,  # Lower temperature for educational content
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            return ai_response.strip() if ai_response else f"I couldn't generate a summary for {topic}."
            
        except Exception as e:
            logger.error(f"Error generating topic summary for '{topic}': {e}")
            return f"I encountered an error while summarizing {topic}. Please try again."
    
    def create_welcome_message(self, user_name: Optional[str] = None) -> str:
        """
        Create a personalized welcome message for new users
        
        Args:
            user_name: User's display name
        
        Returns:
            Welcome message
        """
        greeting = f"Hello {user_name}!" if user_name else "Hello!"
        
        return f"""{greeting} 👋

I'm your AI Daily Digest assistant! I help you stay up-to-date with the latest AI developments by:

🤖 **Daily Digests**: I send curated summaries of the best AI content from Reddit communities
💬 **AI Chat**: Ask me anything about AI, machine learning, or technology trends  
📊 **Insights**: Get explanations of complex AI concepts and developments

**What would you like to know about AI today?**

You can ask me about:
• Recent AI breakthroughs and research
• AI tools and applications
• Machine learning concepts  
• Industry trends and developments
• Specific AI topics you're curious about

Just send me a message and let's chat about AI! 🚀"""
    
    def create_help_message(self) -> str:
        """
        Create a help message explaining bot capabilities
        
        Returns:
            Help message
        """
        return """🤖 **AI Daily Digest Bot Help**

**Commands:**
• `/start` - Get started and see welcome message
• `/help` - Show this help message  
• `/stats` - View processing statistics
• `/digest` - Get today's digest (if available)

**Chat Features:**
💬 **Ask me anything about AI!** I can help with:
• Explaining AI concepts and technologies
• Discussing recent AI developments
• Answering questions about machine learning
• Providing insights about AI trends
• Chatting about the future of AI

**Daily Digests:**
📅 I automatically send curated daily summaries of the best AI content from Reddit communities like r/artificial, r/OpenAI, r/ClaudeAI, and more.

**Examples of what you can ask:**
• "What's new in large language models?"
• "Explain how transformers work"
• "What are the latest AI safety developments?"
• "Tell me about recent AI research breakthroughs"

Just send me any message to start chatting! 🚀"""