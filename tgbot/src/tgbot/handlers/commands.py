"""
Command handlers for the Telegram bot
"""

import logging
from telegram import Update, BotCommand
from telegram.ext import ContextTypes

from ..services.database import BotDatabase
from ..services.digest_generator import DigestGenerator
from ..services.chat_handler import ChatHandler
from ..models.config import BotConfig

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Handles all bot commands"""
    
    def __init__(self, config: BotConfig, database: BotDatabase, 
                 digest_generator: DigestGenerator, chat_handler: ChatHandler):
        self.config = config
        self.database = database
        self.digest_generator = digest_generator
        self.chat_handler = chat_handler
    
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
            # This will be called from the main bot class
            # await self.send_daily_digest()
            await update.message.reply_text("✅ Test digest command received! Implementation depends on main bot class.")
        except Exception as e:
            logger.error(f"Error generating test digest: {e}")
            await update.message.reply_text(f"❌ Error generating test digest: {str(e)}")
    
    @staticmethod
    def get_bot_commands():
        """Get the list of bot commands for the menu"""
        return [
            BotCommand("start", "Get started with the AI Daily Digest bot"),
            BotCommand("help", "Show help and available commands"),
            BotCommand("stats", "View content processing statistics"),
            BotCommand("digest", "Get the latest daily digest")
        ]