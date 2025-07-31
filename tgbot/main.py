"""
AI Daily Digest Telegram Bot - Entry Point
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tgbot.models.config import load_bot_config
from tgbot.bot import AIDigestBot
from tgbot.utils.logging import setup_logging


async def main():
    """Main function to run the bot"""
    try:
        # Setup logging
        setup_logging(level="INFO")
        
        # Load configuration
        bot_config = load_bot_config()
        
        # Create and start the bot
        bot = AIDigestBot(bot_config)
        await bot.start()
        
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error running bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())