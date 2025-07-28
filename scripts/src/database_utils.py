"""
Database utility functions for Reddit fetcher
"""

from typing import Dict, List
from supabase import Client
from postgrest.exceptions import APIError as SupabaseAPIError
from .logging_config import get_script_logger

logger = get_script_logger(__name__)


def batch_check_submissions_exist(supabase: Client, reddit_ids: List[str]) -> Dict[str, bool]:
    """
    Check multiple submissions existence in a single query
    
    Args:
        supabase: Supabase client instance
        reddit_ids: List of Reddit IDs to check
        
    Returns:
        Dict[str, bool]: Mapping of Reddit ID to existence status
    """
    if not reddit_ids:
        return {}
        
    try:
        result = supabase.table('reddit_posts')\
            .select('reddit_id')\
            .in_('reddit_id', reddit_ids)\
            .execute()
            
        existing_ids = {row['reddit_id'] for row in result.data}
        return {reddit_id: reddit_id in existing_ids for reddit_id in reddit_ids}
        
    except SupabaseAPIError as e:
        logger.error(f"Database error batch checking submissions: {e}")
        return {reddit_id: False for reddit_id in reddit_ids}
    except Exception as e:
        logger.error(f"Unexpected error batch checking submissions: {e}")
        return {reddit_id: False for reddit_id in reddit_ids}


def batch_check_comments_exist(supabase: Client, reddit_ids: List[str]) -> Dict[str, bool]:
    """
    Check multiple comments existence in a single query
    
    Args:
        supabase: Supabase client instance
        reddit_ids: List of Reddit IDs to check
        
    Returns:
        Dict[str, bool]: Mapping of Reddit ID to existence status
    """
    if not reddit_ids:
        return {}
        
    try:
        result = supabase.table('reddit_comments')\
            .select('reddit_id')\
            .in_('reddit_id', reddit_ids)\
            .execute()
            
        existing_ids = {row['reddit_id'] for row in result.data}
        return {reddit_id: reddit_id in existing_ids for reddit_id in reddit_ids}
        
    except SupabaseAPIError as e:
        logger.error(f"Database error batch checking comments: {e}")
        return {reddit_id: False for reddit_id in reddit_ids}
    except Exception as e:
        logger.error(f"Unexpected error batch checking comments: {e}")
        return {reddit_id: False for reddit_id in reddit_ids}


def check_subreddit_exists(supabase: Client, subreddit_name: str) -> bool:
    """
    Check if subreddit exists in database
    
    Args:
        supabase: Supabase client instance
        subreddit_name: Name of subreddit to check
        
    Returns:
        bool: True if subreddit exists
    """
    try:
        result = supabase.table('subreddits').select('name').eq('name', subreddit_name).execute()
        return len(result.data) > 0
    except SupabaseAPIError as e:
        logger.error(f"Database error checking if subreddit {subreddit_name} exists: {e}")
        return False
    except ConnectionError as e:
        logger.error(f"Connection error checking subreddit {subreddit_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking if subreddit {subreddit_name} exists: {e}")
        return False


def check_submission_exists(supabase: Client, reddit_id: str) -> bool:
    """
    Check if submission already exists in database
    
    Args:
        supabase: Supabase client instance
        reddit_id: Reddit ID to check
        
    Returns:
        bool: True if submission exists
    """
    try:
        result = supabase.table('reddit_posts').select('reddit_id').eq('reddit_id', reddit_id).execute()
        return len(result.data) > 0
    except SupabaseAPIError as e:
        logger.error(f"Database error checking if submission {reddit_id} exists: {e}")
        return False
    except ConnectionError as e:
        logger.error(f"Connection error checking submission {reddit_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking if submission {reddit_id} exists: {e}")
        return False


def check_comment_exists(supabase: Client, reddit_id: str) -> bool:
    """
    Check if comment already exists in database
    
    Args:
        supabase: Supabase client instance
        reddit_id: Reddit ID to check
        
    Returns:
        bool: True if comment exists
    """
    try:
        result = supabase.table('reddit_comments').select('reddit_id').eq('reddit_id', reddit_id).execute()
        return len(result.data) > 0
    except SupabaseAPIError as e:
        logger.error(f"Database error checking if comment {reddit_id} exists: {e}")
        return False
    except ConnectionError as e:
        logger.error(f"Connection error checking comment {reddit_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking if comment {reddit_id} exists: {e}")
        return False