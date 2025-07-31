"""
Message handlers for chat functionality
"""

import logging
from typing import Dict, List
from telegram import Update
from telegram.ext import ContextTypes

from ..services.chat_handler import ChatHandler

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Handles text messages for chat functionality"""
    
    def __init__(self, chat_handler: ChatHandler):
        self.chat_handler = chat_handler
        # User conversation context (simple in-memory storage)
        self.user_contexts: Dict[int, List[Dict[str, str]]] = {}
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general text messages for chat functionality"""
        user = update.effective_user
        user_message = update.message.text
        
        if not user or not user_message:
            return
        
        user_id = user.id
        user_name = user.first_name
        
        try:
            # Get or create user context
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = []
            
            # Add user message to context
            self.user_contexts[user_id].append({"role": "user", "content": user_message})
            
            # Show typing indicator
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, 
                action="typing"
            )
            
            # Generate AI response
            response = await self.chat_handler.handle_message(
                user_message=user_message,
                user_id=user_id,
                user_name=user_name,
                chat_context=self.user_contexts[user_id]
            )
            
            # Add AI response to context
            self.user_contexts[user_id].append({"role": "assistant", "content": response})
            
            # Keep only last 20 messages in context to manage memory
            if len(self.user_contexts[user_id]) > 20:
                self.user_contexts[user_id] = self.user_contexts[user_id][-20:]
            
            # Send response
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error handling message from user {user_id}: {e}")
            await update.message.reply_text(
                "I encountered an error processing your message. Please try again."
            )
    
    def clear_user_context(self, user_id: int):
        """Clear conversation context for a user"""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
            logger.info(f"Cleared context for user {user_id}")
    
    def get_user_context_size(self, user_id: int) -> int:
        """Get the size of user's conversation context"""
        return len(self.user_contexts.get(user_id, []))