#!/usr/bin/env python3
"""
Test Comment Fetching
Test the comment fetching functionality on a specific submission
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Any, Optional


# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from src.reddit_fetcher import RedditFetcher
from src.config_models import load_config_from_env, FetchConfig
from src.logging_config import setup_logging

# Configure logging
logger = setup_logging(
    level=logging.DEBUG,
    include_console=True
).getChild(__name__)


def test_comment_fetching(submission_url: Optional[str] = None):
    """Test comment fetching on a specific submission"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Load configuration with comment fetching enabled
        reddit_config, supabase_config, _ = load_config_from_env()
        
        # Create a fetch config optimized for testing
        test_fetch_config = FetchConfig(
            fetch_comments=True,
            max_comments_per_post=5,  # Lower for testing
            max_comment_depth=2,
            min_comment_score=1  # Lower threshold for testing
        )
        
        # Initialize fetcher
        fetcher = RedditFetcher(reddit_config, supabase_config, test_fetch_config)
        
        # Use a default test URL if none provided
        if not submission_url:
            # Use a popular AI-related post URL for testing
            submission_url = "https://www.reddit.com/r/artificial/hot/"
            logger.info("No URL provided, fetching from r/artificial hot posts")
            
            # Fetch one post from r/artificial for testing
            subreddit = fetcher.reddit.subreddit('artificial')
            for submission in subreddit.hot(limit=1):
                logger.info(f"Testing with submission: {submission.title}")
                submission_url = f"https://reddit.com{submission.permalink}"
                break
        
        # Get submission from URL
        submission = fetcher.reddit.submission(url=submission_url)
        
        logger.info(f"Testing comment fetching for: {submission.title}")
        logger.info(f"Submission has {submission.num_comments} total comments")
        
        # Check if post exists in database, if not store it first
        if not fetcher.submission_exists(submission.id):
            logger.info("Submission not in database, storing it first...")
            
            # Store the submission using subreddit name
            subreddit_name = submission.subreddit.display_name
            if not fetcher.subreddit_exists(subreddit_name):
                logger.error(f"Subreddit {subreddit_name} not in database")
                return
            
            # Store the submission
            if not fetcher.store_submission(submission, subreddit_name):
                logger.error("Failed to store submission")
                return
            logger.info(f"Stored submission with reddit_id: {submission.id}")
        
        # Fetch comments
        logger.info("Starting comment fetching...")
        comment_count = fetcher.fetch_submission_comments(submission, submission.id)
        
        logger.info(f"Successfully stored {comment_count} comments")
        
        # Get comment statistics from database
        try:
            result = fetcher.supabase.table('reddit_comments')\
                .select('*')\
                .eq('post_reddit_id', submission.id)\
                .execute()
            
            comments = result.data
            logger.info(f"Total comments in database for this post: {len(comments)}")
            
            # Show sample comments
            if comments:
                logger.info("Sample comments:")
                for i, comment in enumerate(comments[:3]):
                    logger.info(f"  {i+1}. Score: {comment['score']}, Depth: {comment['depth']}")
                    logger.info(f"     Content: {comment['content'][:100]}...")
            
        except Exception as e:
            logger.error(f"Error retrieving comment statistics: {e}")
        
        logger.info("Comment fetching test completed successfully")
        
    except Exception as e:
        logger.error(f"Comment fetching test failed: {e}", exc_info=True)


def test_comment_filtering():
    """Test comment filtering logic"""
    logger.info("Testing comment filtering logic...")
    
    # Load config
    load_dotenv()
    reddit_config, supabase_config, fetch_config = load_config_from_env()
    fetcher = RedditFetcher(reddit_config, supabase_config, fetch_config)
    
    # Create mock comment objects for testing
    class MockComment:
        def __init__(self, body, score):
            self.body = body
            self.score = score
    
    test_cases = [
        (MockComment("This is a great analysis of the AI landscape!", 15), True, "Good comment"),
        (MockComment("[deleted]", 5), False, "Deleted comment"),
        (MockComment("yes", 10), False, "Too short/basic"),
        (MockComment("Low quality comment", 1), False, "Low score"),
        (MockComment("Short", 5), False, "Too short"),
        (MockComment("This is a detailed explanation of how the model works and why it's important.", 8), True, "Good detailed comment")
    ]
    
    for comment, expected, description in test_cases:
        result = fetcher._should_include_comment(comment)  # type: ignore
        status = "✓" if result == expected else "✗"
        logger.info(f"{status} {description}: Expected {expected}, Got {result}")
    
    logger.info("Comment filtering test completed")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test comment fetching functionality')
    parser.add_argument('--url', type=str, help='Reddit submission URL to test')
    parser.add_argument('--test-filters', action='store_true', help='Test comment filtering logic')
    
    args = parser.parse_args()
    
    if args.test_filters:
        test_comment_filtering()
    else:
        test_comment_fetching(args.url)


if __name__ == "__main__":
    main()