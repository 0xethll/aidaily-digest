"""
AI Daily Digest Telegram Bot
Main application that handles commands, chat, and scheduled digest delivery.
"""

import asyncio
import logging
from datetime import datetime, timezone, time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from telegram import Update, BotCommand
from telegram.ext import (
    Application, 
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import load_bot_config, BotConfig
from database import BotDatabase
from digest_generator import DigestGenerator
from chat_handler import ChatHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global instances
config: BotConfig
database: BotDatabase
digest_generator: DigestGenerator
chat_handler: ChatHandler
scheduler: AsyncIOScheduler


class AIDigestBot:
    """Main bot application class"""
    
    def __init__(self, bot_config: BotConfig):
        self.config = bot_config
        self.database = BotDatabase(bot_config.supabase)
        self.digest_generator = DigestGenerator(self.database, bot_config.digest)
        self.chat_handler = ChatHandler(bot_config.llm)
        self.scheduler = AsyncIOScheduler()
        self.application: Optional[Application] = None
        
        # User conversation context (simple in-memory storage)
        self.user_contexts: Dict[int, list] = {}
    
    async def setup_application(self) -> Application:
        """Setup and configure the Telegram application"""
        application = ApplicationBuilder().token(self.config.telegram.bot_token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("digest", self.digest_command))
        application.add_handler(CommandHandler("test_digest", self.test_digest_command))
        
        # Message handler for general chat
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        # Set bot commands
        await self.set_bot_commands(application)
        
        return application
    
    async def set_bot_commands(self, application: Application):
        """Set the bot's command menu"""
        commands = [
            BotCommand("start", "Get started with the AI Daily Digest bot"),
            BotCommand("help", "Show help and available commands"),
            BotCommand("stats", "View content processing statistics"),
            BotCommand("digest", "Get the latest daily digest")
        ]
        await application.bot.set_my_commands(commands)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        user = update.effective_user
        user_name = user.first_name if user else None
        
        welcome_message = self.chat_handler.create_welcome_message(user_name)
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        
        logger.info(f"User {user.id} ({user_name}) started the bot")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        help_message = self.chat_handler.create_help_message()
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /stats command"""
        try:
            stats_message = await self.digest_generator.generate_stats_message()
            await update.message.reply_text(stats_message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error generating stats: {e}")
            await update.message.reply_text("❌ Unable to retrieve statistics right now.")
    
    async def digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /digest command - send latest digest"""
        try:
            # Get recent digests
            recent_digests = await self.database.get_recent_digests(limit=1)
            if not recent_digests:
                await update.message.reply_text("📭 No digests available yet. The daily digest is sent automatically each morning!")
                return
            
            latest_digest = recent_digests[0]
            digest_date = latest_digest.get('date', 'Unknown')
            post_count = latest_digest.get('post_count', 0)
            
            message = f"📊 **Latest Digest: {digest_date}**\n\n"
            message += f"📝 Contains {post_count} curated posts\n"
            message += f"⏰ Daily digests are sent automatically each morning\n\n"
            message += "💬 **Want to chat about AI?** Just send me any message!"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error handling digest command: {e}")
            await update.message.reply_text("❌ Unable to retrieve digest information right now.")
    
    async def test_digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /test_digest command - generate and send a test digest"""
        user = update.effective_user
        
        # Only allow admin users to test
        if user.id not in self.config.telegram.admin_chat_ids:
            await update.message.reply_text("🔒 This command is only available to administrators.")
            return
        
        await update.message.reply_text("🔄 Generating test digest...")
        
        try:
            await self.send_daily_digest()
            await update.message.reply_text("✅ Test digest generated and sent!")
        except Exception as e:
            logger.error(f"Error generating test digest: {e}")
            await update.message.reply_text(f"❌ Error generating test digest: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
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
            await update.message.reply_text("I encountered an error processing your message. Please try again.")
    
    async def send_daily_digest(self):
        """Generate and send the daily digest to configured chats"""
        logger.info("Starting daily digest generation...")
        
        try:
            # Generate the digest
            message, digest_id, post_ids = await self.digest_generator.generate_daily_digest()
            
            if not message:
                logger.warning("No digest generated - likely no new content")
                return
            
            # Update digest status to processing
            if digest_id:
                await self.database.update_digest_status(digest_id, 'processing')
            
            # Send to all configured admin chats
            successful_sends = 0
            for chat_id in self.config.telegram.admin_chat_ids:
                try:
                    sent_message = await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    successful_sends += 1
                    
                    # Store the first successful message ID
                    if successful_sends == 1 and digest_id:
                        await self.database.update_digest_status(
                            digest_id, 
                            'completed', 
                            sent_message.message_id
                        )
                    
                    logger.info(f"Sent daily digest to chat {chat_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send digest to chat {chat_id}: {e}")
            
            if successful_sends > 0:
                logger.info(f"Daily digest sent successfully to {successful_sends} chats")
            else:
                logger.error("Failed to send digest to any chats")
                if digest_id:
                    await self.database.update_digest_status(digest_id, 'failed')
                    
        except Exception as e:
            logger.error(f"Error in daily digest generation: {e}")
    
    def setup_scheduler(self):
        """Setup the task scheduler for daily digests"""
        # Parse digest time
        digest_time_parts = self.config.digest.digest_time_utc.split(':')
        digest_hour = int(digest_time_parts[0])
        digest_minute = int(digest_time_parts[1]) if len(digest_time_parts) > 1 else 0
        
        # Schedule daily digest
        self.scheduler.add_job(
            self.send_daily_digest,
            CronTrigger(hour=digest_hour, minute=digest_minute, timezone='UTC'),
            id='daily_digest',
            name='Send Daily Digest',
            replace_existing=True
        )
        
        logger.info(f"Scheduled daily digest for {digest_hour:02d}:{digest_minute:02d} UTC")
    
    async def start(self):
        """Start the bot application"""
        global database, digest_generator, chat_handler, scheduler
        
        # Set global references for the scheduled function
        database = self.database
        digest_generator = self.digest_generator
        chat_handler = self.chat_handler
        scheduler = self.scheduler
        
        # Setup application
        self.application = await self.setup_application()
        
        # Setup and start scheduler
        self.setup_scheduler()
        self.scheduler.start()
        
        logger.info("AI Daily Digest Bot started successfully")
        
        # Start polling
        await self.application.run_polling(
            drop_pending_updates=True,
            stop_signals=None  # Handle shutdown gracefully
        )
    
    async def stop(self):
        """Stop the bot application"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        if self.application:
            await self.application.shutdown()
        
        logger.info("AI Daily Digest Bot stopped")


async def main():
    """Main function to run the bot"""
    try:
        # Load configuration
        bot_config = load_bot_config()
        
        # Create and start the bot
        bot = AIDigestBot(bot_config)
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error running bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
