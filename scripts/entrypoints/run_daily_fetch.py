#!/usr/bin/env python3
"""
Daily Reddit Fetch Script
Run this script daily to fetch the latest AI-related posts from Reddit
"""

import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.reddit_fetcher import RedditFetcher
from src.config.config_models import load_config_from_env
from src.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(
    level=logging.INFO,
    log_file='reddit_fetch.log',
    include_console=True
).getChild(__name__)


def main():
    """Main execution function"""
    logger.info("=" * 50)
    logger.info("Starting daily Reddit fetch process")
    logger.info("=" * 50)
    
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configuration
        logger.info("Loading configuration...")
        reddit_config, supabase_config, fetch_config = load_config_from_env()
        logger.info("Configuration loaded successfully")
        logger.info(f"Comment fetching: {'enabled' if fetch_config.fetch_comments else 'disabled'}")
        if fetch_config.fetch_comments:
            logger.info(f"Comment settings: max {fetch_config.max_comments_per_post} per post, depth {fetch_config.max_comment_depth}, min score {fetch_config.min_comment_score}")
        
        # Initialize fetcher
        logger.info("Initializing Reddit fetcher...")
        fetcher = RedditFetcher(reddit_config, supabase_config, fetch_config)
        logger.info("Reddit fetcher initialized successfully")
        
        # Fetch from all subreddits
        logger.info("Starting to fetch submissions from all target subreddits...")
        results = fetcher.fetch_all_subreddits(limit_per_subreddit=30)
        
        # Calculate totals
        total_posts = sum(results.values())
        successful_subreddits = len([count for count in results.values() if count > 0])
        
        # Log results
        logger.info("=" * 50)
        logger.info("DAILY FETCH RESULTS")
        logger.info("=" * 50)
        logger.info(f"Total new posts fetched: {total_posts}")
        logger.info(f"Successful subreddits: {successful_subreddits}/{len(results)}")
        logger.info("")
        logger.info("Results by subreddit:")
        for subreddit, count in sorted(results.items()):
            status = "✓" if count > 0 else "✗"
            logger.info(f"  {status} r/{subreddit}: {count} posts")
        
        # Get and log daily stats
        logger.info("")
        logger.info("Getting daily statistics...")
        stats = fetcher.get_daily_stats()
        if stats:
            logger.info(f"Daily stats: {stats}")
        
        logger.info("=" * 50)
        logger.info("Daily fetch process completed successfully")
        logger.info("=" * 50)
        
        return 0  # Success
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Daily fetch failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)