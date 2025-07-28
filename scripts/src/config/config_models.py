"""
Configuration data models for Reddit fetcher
"""

import os
from dataclasses import dataclass, field
from typing import List
from supabase import create_client
from postgrest.exceptions import APIError as SupabaseAPIError
from src.utils.logging_config import get_script_logger

logger = get_script_logger(__name__)


@dataclass
class RedditConfig:
    """Configuration for Reddit API access"""
    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str


@dataclass
class SupabaseConfig:
    """Configuration for Supabase database"""
    url: str
    key: str


@dataclass
class FetchConfig:
    """Configuration for fetch behavior"""
    fetch_comments: bool = True
    max_comments_per_post: int = 10
    max_comment_depth: int = 2
    min_comment_score: int = 2
    target_subreddits: List[str] = field(default_factory=list)
    min_submission_score: int = 5
    max_title_length: int = 300
    max_content_length: int = 40000
    max_comment_length: int = 10000


def load_config_from_env() -> tuple[RedditConfig, SupabaseConfig, FetchConfig]:
    """
    Load configuration from environment variables and validate connectivity
    
    Returns:
        tuple: Reddit, Supabase, and Fetch configurations
        
    Raises:
        ValueError: If required environment variables are missing
        ConnectionError: If database connectivity validation fails
    """
    reddit_config = RedditConfig(
        client_id=os.getenv('REDDIT_CLIENT_ID') or '',
        client_secret=os.getenv('REDDIT_CLIENT_SECRET') or '',
        username=os.getenv('REDDIT_USERNAME') or '',
        password=os.getenv('REDDIT_PASSWORD') or '',
        user_agent=os.getenv('REDDIT_USER_AGENT', 'AI Daily Digest Fetcher 1.0')
    )
    
    supabase_config = SupabaseConfig(
        url=os.getenv('SUPABASE_URL') or '',
        key=os.getenv('SUPABASE_ANON_KEY') or ''
    )
    
    # Validate required environment variables
    required_vars = [
        reddit_config.client_id,
        reddit_config.client_secret, 
        reddit_config.username,
        reddit_config.password,
        supabase_config.url,
        supabase_config.key
    ]
    
    if not all(required_vars):
        missing = []
        if not reddit_config.client_id: missing.append('REDDIT_CLIENT_ID')
        if not reddit_config.client_secret: missing.append('REDDIT_CLIENT_SECRET')
        if not reddit_config.username: missing.append('REDDIT_USERNAME')
        if not reddit_config.password: missing.append('REDDIT_PASSWORD')
        if not supabase_config.url: missing.append('SUPABASE_URL')
        if not supabase_config.key: missing.append('SUPABASE_ANON_KEY')
        
        raise ValueError(f"Missing required environment variables: {missing}")
    
    # Validate database connectivity
    _validate_database_connection(supabase_config)
    
    # Parse target subreddits from environment
    target_subreddits_str = os.getenv('TARGET_SUBREDDITS', 'AI_Agents,artificial,ClaudeAI,LangChain,LocalLLaMA,OpenAI,PromptEngineering,singularity')
    target_subreddits = [s.strip() for s in target_subreddits_str.split(',') if s.strip()]
    
    fetch_config = FetchConfig(
        fetch_comments=os.getenv('FETCH_COMMENTS', 'true').lower() == 'true',
        max_comments_per_post=int(os.getenv('MAX_COMMENTS_PER_POST', '10')),
        max_comment_depth=int(os.getenv('MAX_COMMENT_DEPTH', '2')),
        min_comment_score=int(os.getenv('MIN_COMMENT_SCORE', '2')),
        target_subreddits=target_subreddits,
        min_submission_score=int(os.getenv('MIN_SUBMISSION_SCORE', '5')),
        max_title_length=int(os.getenv('MAX_TITLE_LENGTH', '300')),
        max_content_length=int(os.getenv('MAX_CONTENT_LENGTH', '40000')),
        max_comment_length=int(os.getenv('MAX_COMMENT_LENGTH', '10000'))
    )
    
    return reddit_config, supabase_config, fetch_config


def _validate_database_connection(supabase_config: SupabaseConfig) -> None:
    """
    Validate that we can connect to the Supabase database
    
    Args:
        supabase_config: Supabase configuration to test
        
    Raises:
        ConnectionError: If database connection fails
    """
    try:
        # Create a temporary client to test connection
        temp_client = create_client(supabase_config.url, supabase_config.key)
        
        # Try to query the subreddits table to verify connectivity and schema
        result = temp_client.table('subreddits').select('name').limit(1).execute()
        
        if not hasattr(result, 'data'):
            raise ConnectionError("Database query returned unexpected response format")
            
        logger.info("Database connectivity validated successfully")
        
    except SupabaseAPIError as e:
        raise ConnectionError(f"Failed to connect to Supabase database: {e}")
    except Exception as e:
        raise ConnectionError(f"Database validation failed: {e}")