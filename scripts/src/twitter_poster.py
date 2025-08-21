"""
Twitter poster for automated tweeting of high-scoring Reddit posts
"""

import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass

from supabase import create_client
from postgrest.exceptions import APIError as SupabaseAPIError

from src.config.config_models import load_config_from_env
from src.twitter_client import (
    TwitterClient, 
    load_twitter_config_from_env, 
    generate_humorous_tweet_thread
)
from src.utils.logging_config import get_script_logger

logger = get_script_logger(__name__)


@dataclass
class RedditPostForTweet:
    """Reddit post data for tweet generation"""
    reddit_id: str
    title: str
    summary: str  
    url: str
    permalink: str
    score: int
    created_utc: datetime


class TwitterPoster:
    """Automated Twitter posting for high-scoring Reddit posts"""
    
    def __init__(self):
        """Initialize the Twitter poster with database and API clients"""
        try:
            # Load configurations
            self.reddit_config, self.supabase_config, self.fetch_config = load_config_from_env()
            self.twitter_config = load_twitter_config_from_env()
            
            # Initialize clients
            self.supabase_client = create_client(
                self.supabase_config.url, 
                self.supabase_config.key
            )
            self.twitter_client = TwitterClient(self.twitter_config)
            
            logger.info("Twitter poster initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Twitter poster: {e}")
            raise
    
    def get_posts_to_tweet(self, min_score: int = 250, hours_back: int = 48) -> List[RedditPostForTweet]:
        """
        Get Reddit posts suitable for tweeting
        
        Args:
            min_score: Minimum Reddit score for posts
            hours_back: How many hours back to look for posts
            
        Returns:
            List of RedditPostForTweet objects
        """
        try:
            # Calculate time cutoff
            time_cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            # Query for posts that meet criteria and haven't been tweeted
            response = self.supabase_client.table('reddit_posts').select(
                'reddit_id, title, summary, url, permalink, score, created_utc'
            ).gte(
                'created_utc', time_cutoff.isoformat()
            ).gte(
                'score', min_score
            ).eq(
                'twitter_sent', False
            ).not_.is_(
                'summary', 'null'  # Must have AI-generated summary
            ).order(
                'score', desc=True
            ).limit(1).execute()  # Limit to prevent too many tweets at once
            
            if not response.data:
                logger.info("No posts found matching tweet criteria")
                return []
            
            posts = []
            for post_data in response.data:
                # Convert created_utc string to datetime
                created_utc = datetime.fromisoformat(post_data['created_utc'].replace('Z', '+00:00'))
                
                posts.append(RedditPostForTweet(
                    reddit_id=post_data['reddit_id'],
                    title=post_data['title'],
                    summary=post_data['summary'],
                    url=post_data['url'] or '',
                    permalink=post_data['permalink'],
                    score=post_data['score'],
                    created_utc=created_utc
                ))
            
            logger.info(f"Found {len(posts)} posts to potentially tweet")
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching posts to tweet: {e}")
            return []
    
    def mark_post_as_tweeted(self, reddit_id: str) -> bool:
        """
        Mark a post as having been tweeted
        
        Args:
            reddit_id: Reddit post ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.supabase_client.table('reddit_posts').update({
                'twitter_sent': True,
                'twitter_sent_at': datetime.now(timezone.utc).isoformat()
            }).eq('reddit_id', reddit_id).execute()
            
            if response.data:
                logger.info(f"Marked post {reddit_id} as tweeted")
                return True
            else:
                logger.error(f"Failed to mark post {reddit_id} as tweeted")
                return False
                
        except Exception as e:
            logger.error(f"Error marking post {reddit_id} as tweeted: {e}")
            return False
    
    def post_tweet_for_reddit_post(self, post: RedditPostForTweet) -> bool:
        """
        Generate and post a tweet thread for a Reddit post
        
        Args:
            post: RedditPostForTweet object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Generating tweet thread for post: {post.reddit_id} (score: {post.score})")
            
            # Generate humorous tweet thread using OpenAI
            thread = generate_humorous_tweet_thread(
                title=post.title,
                summary=post.summary,
                url=post.url,
                reddit_link=post.permalink
            )
            
            # Post the thread
            tweet_ids = self.twitter_client.post_thread(thread)
            
            # Check if all tweets were posted successfully
            if all(tweet_id is not None for tweet_id in tweet_ids):
                logger.info(f"Successfully posted thread for post {post.reddit_id}: {len(tweet_ids)} tweets")
                
                # Mark post as tweeted in database
                if self.mark_post_as_tweeted(post.reddit_id):
                    return True
                else:
                    logger.error(f"Posted tweets but failed to mark post {post.reddit_id} as tweeted")
                    return False
            else:
                logger.error(f"Failed to post complete thread for post {post.reddit_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting tweet for Reddit post {post.reddit_id}: {e}")
            return False
    
    def run_tweet_posting_cycle(self) -> Dict[str, int]:
        """
        Run a complete cycle of tweet posting
        
        Returns:
            Dictionary with success and failure counts
        """
        logger.info("Starting tweet posting cycle")
        
        # Get posts to tweet
        posts_to_tweet = self.get_posts_to_tweet()
        
        if not posts_to_tweet:
            logger.info("No posts to tweet this cycle")
            return {'attempted': 0, 'successful': 0, 'failed': 0}
        
        results = {'attempted': 0, 'successful': 0, 'failed': 0}
        
        for post in posts_to_tweet:
            results['attempted'] += 1
            
            logger.info(f"Processing post: {post.title[:50]}... (score: {post.score})")
            
            if self.post_tweet_for_reddit_post(post):
                results['successful'] += 1
                logger.info(f"✅ Successfully tweeted post {post.reddit_id}")
            else:
                results['failed'] += 1
                logger.error(f"❌ Failed to tweet post {post.reddit_id}")
            
            # Add a small delay between posts to avoid rate limiting issues
            import time
            time.sleep(5)  # 5 second delay between posts
        
        logger.info(f"Tweet posting cycle completed: {results}")
        return results


def main():
    """Main entry point for the Twitter poster"""
    try:
        poster = TwitterPoster()
        results = poster.run_tweet_posting_cycle()
        
        # Print summary
        print(f"Tweet posting completed:")
        print(f"  Attempted: {results['attempted']}")
        print(f"  Successful: {results['successful']}")
        print(f"  Failed: {results['failed']}")
        
        # Exit with error code if any failures
        if results['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Tweet posting interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error in tweet posting: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()