"""
Main bot application class
"""

import asyncio
import logging
from typing import Optional

from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

from .models.config import BotConfig
from .services.database import BotDatabase
from .services.digest_generator import DigestGenerator
from .services.chat_handler import ChatHandler
from .handlers.commands import CommandHandlers
from .handlers.messages import MessageHandlers
from .utils.scheduler import BotScheduler
from .utils.logging import get_logger

logger = get_logger('bot')


class AIDigestBot:
    """Main bot application class"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        
        # Initialize services
        self.database = BotDatabase(config.supabase)
        self.digest_generator = DigestGenerator(self.database, config.digest)
        self.chat_handler = ChatHandler(config.llm)
        
        # Initialize handlers
        self.command_handlers = CommandHandlers(
            config, self.database, self.digest_generator, self.chat_handler
        )
        self.message_handlers = MessageHandlers(self.chat_handler)
        
        # Initialize scheduler
        self.scheduler = BotScheduler()
        
        # Telegram application
        self.application: Optional[Application] = None
    
    async def setup_application(self) -> Application:
        """Setup and configure the Telegram application"""
        application = ApplicationBuilder().token(self.config.telegram.bot_token).build()
        
        # Register command handlers
        application.add_handler(CommandHandler("start", self.command_handlers.start_command))
        application.add_handler(CommandHandler("help", self.command_handlers.help_command))
        application.add_handler(CommandHandler("stats", self.command_handlers.stats_command))
        application.add_handler(CommandHandler("digest", self.command_handlers.digest_command))
        application.add_handler(CommandHandler("test_digest", self.test_digest_command))
        
        # Register message handler for general chat
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.message_handlers.handle_text_message
        ))
        
        # Set bot commands menu
        await application.bot.set_my_commands(
            CommandHandlers.get_bot_commands()
        )
        
        logger.info("Telegram application configured successfully")
        return application
    
    async def test_digest_command(self, update, context):
        """Handle test digest command - needs access to send_daily_digest"""
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
        self.scheduler.schedule_daily_task(
            func=self.send_daily_digest,
            hour=digest_hour,
            minute=digest_minute,
            timezone='UTC',
            job_id='daily_digest'
        )
        
        logger.info(f"Scheduled daily digest for {digest_hour:02d}:{digest_minute:02d} UTC")
    
    async def start(self):
        """Start the bot application"""
        logger.info("Starting AI Daily Digest Bot...")
        
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
        logger.info("Stopping AI Daily Digest Bot...")
        
        # Stop scheduler
        self.scheduler.shutdown()
        
        # Stop telegram application
        if self.application:
            await self.application.shutdown()
        
        logger.info("AI Daily Digest Bot stopped")