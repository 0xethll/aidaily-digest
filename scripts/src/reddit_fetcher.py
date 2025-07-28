"""
Reddit Fetcher for AI Daily Digest (v2)
Updated to use reddit_id as primary keys for better performance
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


@dataclass
class FetchConfig:
    """Configuration for fetch behavior"""
    fetch_comments: bool = True
    max_comments_per_post: int = 10
    max_comment_depth: int = 2
    min_comment_score: int = 2


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
    
    def __init__(self, reddit_config: RedditConfig, supabase_config: SupabaseConfig, fetch_config: FetchConfig = None):
        self.reddit_config = reddit_config
        self.supabase_config = supabase_config
        self.fetch_config = fetch_config or FetchConfig()
        
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
    
    def subreddit_exists(self, subreddit_name: str) -> bool:
        """Check if subreddit exists in database"""
        try:
            result = self.supabase.table('subreddits').select('name').eq('name', subreddit_name).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking if subreddit exists: {e}")
            return False
    
    def submission_exists(self, reddit_id: str) -> bool:
        """Check if submission already exists in database"""
        try:
            result = self.supabase.table('reddit_posts').select('reddit_id').eq('reddit_id', reddit_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking if submission exists: {e}")
            return False
    
    def comment_exists(self, reddit_id: str) -> bool:
        """Check if comment already exists in database"""
        try:
            result = self.supabase.table('reddit_comments').select('reddit_id').eq('reddit_id', reddit_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking if comment exists: {e}")
            return False
    
    def store_submission(self, submission: praw.models.Submission, subreddit_name: str) -> bool:
        """Store or update a Reddit submission in Supabase"""
        try:
            
            # Prepare submission data
            submission_data = {
                'reddit_id': submission.id,
                'subreddit_name': subreddit_name,
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
            
            # Upsert into database (insert or update if exists)
            result = self.supabase.table('reddit_posts').upsert(submission_data).execute()
            
            if result.data:
                logger.info(f"Stored/updated submission: {submission.title[:50]}...")
                return True
            else:
                logger.error(f"Failed to store/update submission: {submission.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing submission {submission.id}: {e}")
            return False
    
    def store_comment(self, comment: praw.models.Comment, post_reddit_id: str, parent_comment_reddit_id: Optional[str] = None, depth: int = 0) -> bool:
        """Store or update a Reddit comment in Supabase"""
        try:
            
            # Skip deleted/removed comments
            if comment.body in ['[deleted]', '[removed]', None]:
                return False
            
            # Prepare comment data
            comment_data = {
                'reddit_id': comment.id,
                'post_reddit_id': post_reddit_id,
                'parent_comment_reddit_id': parent_comment_reddit_id,
                'content': comment.body,
                'score': comment.score,
                'author': str(comment.author) if comment.author else None,
                'created_utc': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat(),
                'is_submitter': comment.is_submitter,
                'depth': depth
            }
            
            # Upsert into database (insert or update if exists)
            result = self.supabase.table('reddit_comments').upsert(comment_data).execute()
            
            if result.data:
                logger.debug(f"Stored/updated comment: {comment.body[:30]}...")
                return True
            else:
                logger.error(f"Failed to store/update comment: {comment.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing comment {comment.id}: {e}")
            return False
    
    def fetch_submission_comments(self, submission: praw.models.Submission, post_reddit_id: str) -> int:
        """Fetch and store comments for a submission"""
        if not self.fetch_config.fetch_comments:
            return 0
        
        stored_count = 0
        
        try:
            # Replace "more comments" with actual comments up to a limit
            submission.comments.replace_more(limit=0)
            
            # Get top-level comments
            comments_processed = 0
            for comment in submission.comments:
                if comments_processed >= self.fetch_config.max_comments_per_post:
                    break
                
                if self._should_include_comment(comment):
                    if self.store_comment(comment, post_reddit_id, depth=0):
                        stored_count += 1
                        comments_processed += 1
                        
                        # Fetch replies if within depth limit
                        if self.fetch_config.max_comment_depth > 0:
                            stored_count += self._fetch_comment_replies(
                                comment, post_reddit_id, comment.id, 1
                            )
                
                # Small delay between comment processing
                time.sleep(0.05)
            
            if stored_count > 0:
                logger.info(f"Stored {stored_count} comments for submission {submission.id}")
            
            return stored_count
            
        except Exception as e:
            logger.error(f"Error fetching comments for submission {submission.id}: {e}")
            return 0
    
    def _fetch_comment_replies(self, parent_comment: praw.models.Comment, post_reddit_id: str, parent_comment_reddit_id: str, depth: int) -> int:
        """Recursively fetch comment replies up to max depth"""
        stored_count = 0
        
        if depth >= self.fetch_config.max_comment_depth:
            return 0
        
        try:
            parent_comment.replies.replace_more(limit=0)
            
            for reply in parent_comment.replies:
                if self._should_include_comment(reply):
                    if self.store_comment(reply, post_reddit_id, parent_comment_reddit_id, depth):
                        stored_count += 1
                        
                        # Continue recursively if within depth limit
                        if depth + 1 < self.fetch_config.max_comment_depth:
                            stored_count += self._fetch_comment_replies(
                                reply, post_reddit_id, reply.id, depth + 1
                            )
                
                time.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Error fetching replies for comment {parent_comment.id}: {e}")
        
        return stored_count
    
    def _should_include_comment(self, comment: praw.models.Comment) -> bool:
        """Apply content filtering rules for comments"""
        # Skip deleted/removed comments
        if comment.body in ['[deleted]', '[removed]', None]:
            return False
        
        # Skip low-score comments (configurable threshold)
        if comment.score < self.fetch_config.min_comment_score:
            return False
        
        # Skip very short comments
        if len(comment.body.strip()) < 10:
            return False
        
        # Skip comments that are just links or very basic responses
        if comment.body.strip().lower() in ['this', 'same', 'yes', 'no', 'lol', 'thanks']:
            return False
        
        return True
    
    def fetch_subreddit_submissions(
        self, 
        subreddit_name: str, 
        limit: int = 25,
    ) -> int:
        """Fetch submissions from a specific subreddit"""
        logger.info(f"Fetching submissions from r/{subreddit_name}")
        
        # Check if subreddit exists in database
        if not self.subreddit_exists(subreddit_name):
            logger.error(f"Subreddit {subreddit_name} not found in database")
            return 0
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            stored_count = 0
            
            for submission in subreddit.hot(limit=limit):                
                # Apply basic filtering
                if self._should_include_submission(submission):
                    if self.store_submission(submission, subreddit_name):
                        stored_count += 1
                        
                        # Fetch comments for this submission if enabled
                        if self.fetch_config.fetch_comments:
                            self.fetch_submission_comments(submission, submission.id)
                
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
        if self.fetch_config.fetch_comments:
            logger.info(f"Comment fetching enabled: max {self.fetch_config.max_comments_per_post} comments per post, depth {self.fetch_config.max_comment_depth}")
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
                'total_comments': 0,
                'comment_stats': {
                    'total_comments_stored': 0,
                    'avg_comments_per_post': 0
                }
            }
            
            # Get comment statistics if comments are being fetched
            if self.fetch_config.fetch_comments:
                comment_result = self.supabase.table('reddit_comments')\
                    .select('*')\
                    .gte('fetched_at', date.isoformat())\
                    .lt('fetched_at', (date + timedelta(days=1)).isoformat())\
                    .execute()
                
                stats['comment_stats']['total_comments_stored'] = len(comment_result.data)
                if posts:
                    stats['comment_stats']['avg_comments_per_post'] = len(comment_result.data) / len(posts)
            
            if posts:
                stats['avg_score'] = sum(post['score'] for post in posts) / len(posts)
                stats['total_comments'] = sum(post['num_comments'] for post in posts)
                
                # Group by subreddit
                for post in posts:
                    subreddit_name = post['subreddit_name']
                    stats['posts_by_subreddit'][subreddit_name] = stats['posts_by_subreddit'].get(subreddit_name, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {}


def load_config_from_env() -> tuple[RedditConfig, SupabaseConfig, FetchConfig]:
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
    
    fetch_config = FetchConfig(
        fetch_comments=os.getenv('FETCH_COMMENTS', 'true').lower() == 'true',
        max_comments_per_post=int(os.getenv('MAX_COMMENTS_PER_POST', '10')),
        max_comment_depth=int(os.getenv('MAX_COMMENT_DEPTH', '2')),
        min_comment_score=int(os.getenv('MIN_COMMENT_SCORE', '2'))
    )
    
    return reddit_config, supabase_config, fetch_config


def main():
    """Main function for testing the fetcher"""
    try:
        # Load configuration
        reddit_config, supabase_config, fetch_config = load_config_from_env()
        
        # Initialize fetcher
        fetcher = RedditFetcher(reddit_config, supabase_config, fetch_config)
        
        # Fetch from all subreddits
        results = fetcher.fetch_all_subreddits(limit_per_subreddit=25)
        
        # Print results
        print(f"Fetch completed:")
        for subreddit, count in results.items():
            print(f"  r/{subreddit}: {count} new posts")
        
        # Print configuration
        print(f"\nConfiguration:")
        print(f"  Comments enabled: {fetch_config.fetch_comments}")
        if fetch_config.fetch_comments:
            print(f"  Max comments per post: {fetch_config.max_comments_per_post}")
            print(f"  Max comment depth: {fetch_config.max_comment_depth}")
            print(f"  Min comment score: {fetch_config.min_comment_score}")
        
        # Get daily stats
        stats = fetcher.get_daily_stats()
        print(f"\nDaily stats: {stats}")
        
    except Exception as e:
        logger.error(f"Failed to run fetcher: {e}")
        raise


if __name__ == "__main__":
    main()