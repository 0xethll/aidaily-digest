"""
Configuration module for the Telegram bot.
Loads settings from environment variables and provides structured config objects.
"""

import os
from dataclasses import dataclass
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class TelegramConfig:
    """Configuration for Telegram bot"""
    bot_token: str
    admin_chat_ids: List[int]  # Chat IDs that can receive digest messages
    webhook_url: Optional[str] = None
    webhook_port: Optional[int] = None


@dataclass
class SupabaseConfig:
    """Configuration for Supabase database"""
    url: str
    key: str


@dataclass
class LLMConfig:
    """Configuration for LLM integration"""
    fireworks_api_key: str
    model_name: str = "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new"
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: float = 30.0


@dataclass
class DigestConfig:
    """Configuration for daily digest generation"""
    digest_time_utc: str = "08:00"  # UTC time to send digest (8 AM UTC)
    max_posts_per_digest: int = 15
    categories_order: List[str] = None
    
    def __post_init__(self):
        if self.categories_order is None:
            self.categories_order = [
                'news', 'tool', 'research', 'tutorial', 
                'discussion', 'showcase', 'question', 'other'
            ]


@dataclass
class BotConfig:
    """Main bot configuration combining all settings"""
    telegram: TelegramConfig
    supabase: SupabaseConfig
    llm: LLMConfig
    digest: DigestConfig


def load_bot_config() -> BotConfig:
    """Load bot configuration from environment variables"""
    
    # Telegram configuration
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    
    # Parse admin chat IDs (comma-separated)
    admin_chat_ids_str = os.getenv('TELEGRAM_ADMIN_CHAT_IDS', '')
    admin_chat_ids = []
    if admin_chat_ids_str:
        try:
            admin_chat_ids = [int(chat_id.strip()) for chat_id in admin_chat_ids_str.split(',')]
        except ValueError:
            raise ValueError("TELEGRAM_ADMIN_CHAT_IDS must be comma-separated integers")
    
    telegram_config = TelegramConfig(
        bot_token=bot_token,
        admin_chat_ids=admin_chat_ids,
        webhook_url=os.getenv('TELEGRAM_WEBHOOK_URL'),
        webhook_port=int(os.getenv('TELEGRAM_WEBHOOK_PORT', '8443'))
    )
    
    # Supabase configuration
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
    
    supabase_config = SupabaseConfig(
        url=supabase_url,
        key=supabase_key
    )
    
    # LLM configuration
    fireworks_api_key = os.getenv('FIREWORKS_API_KEY')
    if not fireworks_api_key:
        raise ValueError("FIREWORKS_API_KEY environment variable is required")
    
    llm_config = LLMConfig(
        fireworks_api_key=fireworks_api_key,
        model_name=os.getenv('FIREWORKS_MODEL', 'accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new'),
        temperature=float(os.getenv('LLM_TEMPERATURE', '0.3')),
        max_tokens=int(os.getenv('LLM_MAX_TOKENS', '2000')),
        timeout=float(os.getenv('LLM_TIMEOUT', '30.0'))
    )
    
    # Digest configuration
    digest_config = DigestConfig(
        digest_time_utc=os.getenv('DIGEST_TIME_UTC', '08:00'),
        max_posts_per_digest=int(os.getenv('MAX_POSTS_PER_DIGEST', '15'))
    )
    
    return BotConfig(
        telegram=telegram_config,
        supabase=supabase_config,
        llm=llm_config,
        digest=digest_config
    )