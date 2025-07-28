"""
Reddit Fetcher for AI Daily Digest
Fetches submissions from AI-related subreddits and stores them in Supabase
"""

import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import praw
from supabase import create_client, Client
from prawcore.exceptions import TooManyRequests, ServerError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


class RedditFetcher:
    """Fetches Reddit submissions and stores them in Supabase"""
    
    TARGET_SUBREDDITS = [
        'AI_Agents',
        'artificial', 
        'ClaudeAI',
        'huggingface',
        'LangChain',
        'LocalLLaMA',
        'OpenAI',
        'PromptEngineering',
        'singularity'
    ]
    
    def __init__(self, reddit_config: RedditConfig, supabase_config: SupabaseConfig):
        self.reddit_config = reddit_config
        self.supabase_config = supabase_config
        
        # Initialize Reddit client
        self.reddit = praw.Reddit(
            client_id=reddit_config.client_id,
            client_secret=reddit_config.client_secret,
            username=reddit_config.username,
            password=reddit_config.password,
            user_agent=reddit_config.user_agent,
            ratelimit_seconds=300  # Wait up to 5 minutes for rate limits
        )
        
        # Initialize Supabase client
        self.supabase: Client = create_client(
            supabase_config.url,
            supabase_config.key
        )
        
        # Verify Reddit connection
        try:
            logger.info(f"Connected to Reddit as: {self.reddit.user.me()}")
        except Exception as e:
            logger.error(f"Failed to connect to Reddit: {e}")
            raise
    
    def get_subreddit_id(self, subreddit_name: str) -> Optional[str]:
        """Get subreddit ID from database"""
        try:
            result = self.supabase.table('subreddits').select('id').eq('name', subreddit_name).execute()
            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error getting subreddit ID for {subreddit_name}: {e}")
            return None
    
    def submission_exists(self, reddit_id: str) -> bool:
        """Check if submission already exists in database"""
        try:
            result = self.supabase.table('reddit_posts').select('id').eq('reddit_id', reddit_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking if submission exists: {e}")
            return False
    
    def store_submission(self, submission: praw.models.Submission, subreddit_id: str) -> bool:
        """Store a Reddit submission in Supabase"""
        try:
            # Skip if already exists
            if self.submission_exists(submission.id):
                logger.debug(f"Submission {submission.id} already exists, skipping")
                return True
            
            # Prepare submission data
            submission_data = {
                'reddit_id': submission.id,
                'subreddit_id': subreddit_id,
                'title': submission.title,
                'content': submission.selftext if submission.is_self else None,
                'url': submission.url if not submission.is_self else None,
                'score': submission.score,
                'num_comments': submission.num_comments,
                'upvote_ratio': submission.upvote_ratio,
                'author': str(submission.author) if submission.author else None,
                'created_utc': datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat(),
                'is_stickied': submission.stickied,
                'is_nsfw': submission.over_18,
                'is_self': submission.is_self,
                'permalink': f"https://reddit.com{submission.permalink}",
                'thumbnail': submission.thumbnail if hasattr(submission, 'thumbnail') else None
            }
            
            # Insert into database
            result = self.supabase.table('reddit_posts').insert(submission_data).execute()
            
            if result.data:
                logger.info(f"Stored submission: {submission.title[:50]}...")
                return True
            else:
                logger.error(f"Failed to store submission: {submission.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing submission {submission.id}: {e}")
            return False
    
    def fetch_subreddit_submissions(
        self, 
        subreddit_name: str, 
        limit: int = 25,
        time_filter: str = "day"
    ) -> int:
        """Fetch submissions from a specific subreddit"""
        logger.info(f"Fetching submissions from r/{subreddit_name}")
        
        # Get subreddit ID
        subreddit_id = self.get_subreddit_id(subreddit_name)
        if not subreddit_id:
            logger.error(f"Subreddit {subreddit_name} not found in database")
            return 0
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            stored_count = 0
            
            # Fetch hot posts from the last 24 hours
            for submission in subreddit.hot(limit=limit):
                # Check if post is from the last 24 hours
                post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                
                if post_time < cutoff_time:
                    continue
                
                # Apply basic filtering
                if self._should_include_submission(submission):
                    if self.store_submission(submission, subreddit_id):
                        stored_count += 1
                
                # Rate limiting - small delay between requests
                time.sleep(0.1)
            
            logger.info(f"Stored {stored_count} new submissions from r/{subreddit_name}")
            return stored_count
            
        except TooManyRequests as e:
            logger.warning(f"Rate limited while fetching r/{subreddit_name}: {e}")
            raise
        except ServerError as e:
            logger.error(f"Server error while fetching r/{subreddit_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching r/{subreddit_name}: {e}")
            return 0
    
    def _should_include_submission(self, submission: praw.models.Submission) -> bool:
        """Apply content filtering rules"""
        # Skip stickied posts
        if submission.stickied:
            return False
        
        # Skip low-score posts (configurable threshold)
        if submission.score < 5:
            return False
        
        # Skip deleted/removed posts
        if submission.selftext == '[deleted]' or submission.selftext == '[removed]':
            return False
        
        # Skip if title is too short
        if len(submission.title.strip()) < 10:
            return False
        
        return True
    
    def fetch_all_subreddits(self, limit_per_subreddit: int = 25) -> Dict[str, int]:
        """Fetch submissions from all target subreddits"""
        logger.info("Starting daily Reddit fetch")
        results = {}
        total_stored = 0
        
        for subreddit_name in self.TARGET_SUBREDDITS:
            try:
                count = self.fetch_subreddit_submissions(subreddit_name, limit_per_subreddit)
                results[subreddit_name] = count
                total_stored += count
                
                # Rate limiting between subreddits
                time.sleep(2)
                
            except TooManyRequests:
                logger.warning(f"Rate limited, waiting 60 seconds before continuing...")
                time.sleep(60)
                # Retry once
                try:
                    count = self.fetch_subreddit_submissions(subreddit_name, limit_per_subreddit)
                    results[subreddit_name] = count
                    total_stored += count
                except Exception as retry_error:
                    logger.error(f"Failed to fetch r/{subreddit_name} after retry: {retry_error}")
                    results[subreddit_name] = 0
            
            except Exception as e:
                logger.error(f"Failed to fetch r/{subreddit_name}: {e}")
                results[subreddit_name] = 0
        
        logger.info(f"Fetch completed. Total new submissions: {total_stored}")
        logger.info(f"Results by subreddit: {results}")
        
        return results
    
    def get_daily_stats(self, date: datetime = None) -> Dict[str, Any]:
        """Get statistics for posts fetched on a specific date"""
        if date is None:
            date = datetime.now(timezone.utc).date()
        
        try:
            # Get posts from the specified date
            result = self.supabase.table('reddit_posts')\
                .select('*')\
                .gte('fetched_at', date.isoformat())\
                .lt('fetched_at', (date + timedelta(days=1)).isoformat())\
                .execute()
            
            posts = result.data
            
            # Calculate statistics
            stats = {
                'date': date.isoformat(),
                'total_posts': len(posts),
                'posts_by_subreddit': {},
                'avg_score': 0,
                'total_comments': 0
            }
            
            if posts:
                stats['avg_score'] = sum(post['score'] for post in posts) / len(posts)
                stats['total_comments'] = sum(post['num_comments'] for post in posts)
                
                # Group by subreddit
                for post in posts:
                    subreddit_result = self.supabase.table('subreddits')\
                        .select('name')\
                        .eq('id', post['subreddit_id'])\
                        .execute()
                    
                    if subreddit_result.data:
                        subreddit_name = subreddit_result.data[0]['name']
                        stats['posts_by_subreddit'][subreddit_name] = stats['posts_by_subreddit'].get(subreddit_name, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {}


def load_config_from_env() -> tuple[RedditConfig, SupabaseConfig]:
    """Load configuration from environment variables"""
    reddit_config = RedditConfig(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        username=os.getenv('REDDIT_USERNAME'),
        password=os.getenv('REDDIT_PASSWORD'),
        user_agent=os.getenv('REDDIT_USER_AGENT', 'AI Daily Digest Fetcher 1.0')
    )
    
    supabase_config = SupabaseConfig(
        url=os.getenv('SUPABASE_URL'),
        key=os.getenv('SUPABASE_ANON_KEY')
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
    
    return reddit_config, supabase_config


def main():
    """Main function for testing the fetcher"""
    try:
        # Load configuration
        reddit_config, supabase_config = load_config_from_env()
        
        # Initialize fetcher
        fetcher = RedditFetcher(reddit_config, supabase_config)
        
        # Fetch from all subreddits
        results = fetcher.fetch_all_subreddits(limit_per_subreddit=25)
        
        # Print results
        print(f"Fetch completed:")
        for subreddit, count in results.items():
            print(f"  r/{subreddit}: {count} new posts")
        
        # Get daily stats
        stats = fetcher.get_daily_stats()
        print(f"\nDaily stats: {stats}")
        
    except Exception as e:
        logger.error(f"Failed to run fetcher: {e}")
        raise


if __name__ == "__main__":
    main()