#!/usr/bin/env python3

"""
Entrypoint to print the thread for Twitter posting
Only generates and prints the thread without posting to Twitter
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.twitter_poster import TwitterPoster
from src.twitter_client import generate_humorous_tweet_thread
from src.utils.logging_config import get_script_logger

logger = get_script_logger(__name__)


def main():
    """Main entry point to print Twitter thread without posting"""
    try:
        # Initialize the poster to get access to database
        poster = TwitterPoster()
        
        # Get posts that would be tweeted
        posts_to_tweet = poster.get_posts_to_tweet()
        
        if not posts_to_tweet:
            print("No posts found matching tweet criteria")
            return
        
        # Process the first post
        post = posts_to_tweet[0]
        
        print(f"Reddit ID: {post.reddit_id}")
        print(f"Post: {post.title}")
        print(f"Score: {post.score}")
        print(f"Created: {post.created_utc}")
        print(f"URL: {post.url}")
        print(f"Reddit Link: {post.permalink}")
        print("-" * 50)
        print("Generated Thread:")
        print("-" * 50)
        
        # Generate the thread
        thread = generate_humorous_tweet_thread(
            title=post.title,
            summary=post.summary,
            url=post.url,
            reddit_link=post.permalink
        )
        
        # Print each tweet in the thread
        for i, tweet in enumerate(thread.tweets, 1):
            print(f"Tweet {i}:")
            print(tweet)
            print("-" * 30)
            
    except KeyboardInterrupt:
        logger.info("Thread printing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error generating thread: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()