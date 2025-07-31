"""
Database operations for the Telegram bot.
Handles fetching processed posts, managing digests, and storing bot-related data.
"""

import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
from supabase import Client, create_client
from postgrest.exceptions import APIError as SupabaseAPIError

from config import SupabaseConfig

logger = logging.getLogger(__name__)


class BotDatabase:
    """Database interface for the Telegram bot"""
    
    def __init__(self, config: SupabaseConfig):
        self.config = config
        self.client: Client = create_client(config.url, config.key)
    
    async def get_posts_for_digest(
        self, 
        days_back: int = 1, 
        limit: int = 50,
        categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get processed posts for digest generation
        
        Args:
            days_back: Number of days to look back for posts
            limit: Maximum number of posts to retrieve
            categories: List of categories to include (optional)
        
        Returns:
            List of post dictionaries sorted by score (highest first)
        """
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)
            
            query = self.client.table('reddit_posts')\
                .select('*')\
                .eq('processing_status', 'processed')\
                .not_.is_('summary', 'null')\
                .gte('created_utc', start_date.isoformat())\
                .lte('created_utc', end_date.isoformat())\
                .order('score', desc=True)\
                .limit(limit)
            
            # Add category filter if specified
            if categories:
                query = query.in_('content_type', categories)
            
            result = query.execute()
            posts = result.data or []
            
            logger.info(f"Retrieved {len(posts)} posts for digest from last {days_back} days")
            return posts
            
        except SupabaseAPIError as e:
            logger.error(f"Database error fetching posts for digest: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching posts for digest: {e}")
            return []
    
    async def get_posts_by_category(
        self, 
        days_back: int = 1,
        categories_order: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get posts grouped by category for organized digest
        
        Args:
            days_back: Number of days to look back
            categories_order: Desired order of categories
        
        Returns:
            Dictionary with categories as keys and lists of posts as values
        """
        try:
            posts = await self.get_posts_for_digest(days_back=days_back, limit=100)
            
            # Group posts by category
            posts_by_category = {}
            for post in posts:
                category = post.get('content_type', 'other')
                if category not in posts_by_category:
                    posts_by_category[category] = []
                posts_by_category[category].append(post)
            
            # Sort posts within each category by score
            for category in posts_by_category:
                posts_by_category[category].sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # If categories_order is provided, return in that order
            if categories_order:
                ordered_dict = {}
                for category in categories_order:
                    if category in posts_by_category:
                        ordered_dict[category] = posts_by_category[category]
                
                # Add any remaining categories not in the order
                for category, posts_list in posts_by_category.items():
                    if category not in ordered_dict:
                        ordered_dict[category] = posts_list
                
                return ordered_dict
            
            return posts_by_category
            
        except Exception as e:
            logger.error(f"Error getting posts by category: {e}")
            return {}
    
    async def create_digest_record(
        self, 
        date_for_digest: date, 
        post_count: int,
        summary: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new digest record in the database
        
        Args:
            date_for_digest: Date the digest is for
            post_count: Number of posts included
            summary: Optional summary of the digest
        
        Returns:
            Digest ID if successful, None otherwise
        """
        try:
            digest_data = {
                'date': date_for_digest.isoformat(),
                'post_count': post_count,
                'summary': summary,
                'status': 'pending'
            }
            
            result = self.client.table('daily_digests')\
                .insert(digest_data)\
                .execute()
            
            if result.data:
                digest_id = result.data[0]['id']
                logger.info(f"Created digest record {digest_id} for {date_for_digest}")
                return digest_id
            
            return None
            
        except SupabaseAPIError as e:
            logger.error(f"Database error creating digest record: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating digest record: {e}")
            return None
    
    async def update_digest_status(
        self, 
        digest_id: str, 
        status: str,
        telegram_message_id: Optional[int] = None
    ) -> bool:
        """
        Update digest status and optionally store Telegram message ID
        
        Args:
            digest_id: Digest UUID
            status: New status ('processing', 'completed', 'failed')
            telegram_message_id: Telegram message ID if sent
        
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {'status': status}
            if telegram_message_id:
                update_data['telegram_message_id'] = telegram_message_id
            
            result = self.client.table('daily_digests')\
                .update(update_data)\
                .eq('id', digest_id)\
                .execute()
            
            if result.data:
                logger.info(f"Updated digest {digest_id} status to {status}")
                return True
            
            return False
            
        except SupabaseAPIError as e:
            logger.error(f"Database error updating digest status: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating digest status: {e}")
            return False
    
    async def add_posts_to_digest(
        self, 
        digest_id: str, 
        post_reddit_ids: List[str]
    ) -> bool:
        """
        Add posts to a digest record via junction table
        
        Args:
            digest_id: Digest UUID
            post_reddit_ids: List of Reddit post IDs to include
        
        Returns:
            True if successful, False otherwise
        """
        try:
            digest_posts_data = [
                {
                    'digest_id': digest_id,
                    'post_reddit_id': reddit_id
                }
                for reddit_id in post_reddit_ids
            ]
            
            result = self.client.table('digest_posts')\
                .insert(digest_posts_data)\
                .execute()
            
            if result.data:
                logger.info(f"Added {len(post_reddit_ids)} posts to digest {digest_id}")
                return True
            
            return False
            
        except SupabaseAPIError as e:
            logger.error(f"Database error adding posts to digest: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding posts to digest: {e}")
            return False
    
    async def check_digest_exists_for_date(self, date_for_digest: date) -> bool:
        """
        Check if a digest already exists for a given date
        
        Args:
            date_for_digest: Date to check
        
        Returns:
            True if digest exists, False otherwise
        """
        try:
            result = self.client.table('daily_digests')\
                .select('id')\
                .eq('date', date_for_digest.isoformat())\
                .execute()
            
            return len(result.data or []) > 0
            
        except Exception as e:
            logger.error(f"Error checking digest existence: {e}")
            return False
    
    async def get_recent_digests(self, limit: int = 7) -> List[Dict[str, Any]]:
        """
        Get recent digest records
        
        Args:
            limit: Number of recent digests to retrieve
        
        Returns:
            List of digest records
        """
        try:
            result = self.client.table('daily_digests')\
                .select('*')\
                .order('date', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting recent digests: {e}")
            return []
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about processed content
        
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Total posts
            total_result = self.client.table('reddit_posts')\
                .select('reddit_id', count='exact')\
                .execute()
            total_posts = total_result.count or 0
            
            # Processed posts
            processed_result = self.client.table('reddit_posts')\
                .select('reddit_id', count='exact')\
                .eq('processing_status', 'processed')\
                .execute()
            processed_posts = processed_result.count or 0
            
            # Posts by category
            category_result = self.client.table('reddit_posts')\
                .select('content_type')\
                .eq('processing_status', 'processed')\
                .execute()
            
            category_counts = {}
            for post in category_result.data or []:
                category = post.get('content_type', 'other')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            return {
                'total_posts': total_posts,
                'processed_posts': processed_posts,
                'processing_rate': round((processed_posts / total_posts * 100), 2) if total_posts > 0 else 0,
                'category_breakdown': category_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}