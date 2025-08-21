#!/usr/bin/env python3

"""
Test script for the Twitter poster functionality
Tests thread generation and database integration without actually posting to Twitter
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.twitter_poster import TwitterPoster, RedditPostForTweet
from src.twitter_client import generate_humorous_tweet_thread
from src.utils.logging_config import get_script_logger

logger = get_script_logger(__name__)


def test_tweet_thread_generation():
    """Test the tweet thread generation functionality"""
    print("🧪 Testing tweet thread generation...")
    
    # Sample data
    title = "New AI Model Achieves 99.9% Accuracy on Benchmark Tests"
    summary = "Researchers have developed a revolutionary AI model that outperforms previous state-of-the-art systems by achieving 99.9% accuracy on standard benchmark tests. The model uses a novel architecture combining transformer networks with quantum-inspired algorithms. This breakthrough could lead to significant improvements in natural language processing, computer vision, and autonomous systems. The team plans to open-source their work next month."
    url = "https://example.com/ai-breakthrough"
    reddit_link = "https://reddit.com/r/artificial/comments/abc123/new_ai_model_breakthrough"
    
    try:
        thread = generate_humorous_tweet_thread(title, summary, url, reddit_link)
        
        print(f"✅ Generated thread with {len(thread.tweets)} tweets:")
        for i, tweet in enumerate(thread.tweets, 1):
            print(f"\n📱 Tweet {i} ({len(tweet)} chars):")
            print(f"   {tweet}")
        
        # Validate tweet lengths
        for i, tweet in enumerate(thread.tweets, 1):
            if len(tweet) > 280:
                print(f"❌ Tweet {i} exceeds 280 characters: {len(tweet)}")
                return False
        
        print("\n✅ All tweets are within character limits")
        return True
        
    except Exception as e:
        print(f"❌ Error generating tweet thread: {e}")
        print("ℹ️  This might be due to missing OpenAI API key - fallback should still work")
        return False


def test_database_query():
    """Test the database query functionality"""
    print("\n🧪 Testing database query...")
    
    try:
        poster = TwitterPoster()
        
        # Test getting posts (with lower score threshold for testing)
        posts = poster.get_posts_to_tweet(min_score=50, hours_back=168)  # Last week, lower threshold
        
        if posts:
            print(f"✅ Found {len(posts)} posts in database")
            for i, post in enumerate(posts[:3], 1):  # Show first 3
                print(f"\n📄 Post {i}:")
                print(f"   Title: {post.title[:50]}...")
                print(f"   Score: {post.score}")
                print(f"   Has summary: {'Yes' if post.summary else 'No'}")
        else:
            print("ℹ️  No posts found matching criteria (this is normal if database is empty)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        return False


def test_configuration_loading():
    """Test configuration loading"""
    print("\n🧪 Testing configuration loading...")
    
    try:
        from src.config.config_models import load_config_from_env
        from src.twitter_client import load_twitter_config_from_env
        
        # Test Reddit/Supabase config
        reddit_config, supabase_config, fetch_config = load_config_from_env()
        print("✅ Reddit and Supabase configuration loaded")
        
        # Test Twitter config (this will fail if env vars not set)
        try:
            twitter_config = load_twitter_config_from_env()
            print("✅ Twitter configuration loaded")
        except ValueError as e:
            print(f"⚠️  Twitter configuration missing (expected for testing): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Twitter Poster Implementation\n")
    
    tests = [
        ("Thread Generation", test_tweet_thread_generation),
        ("Configuration Loading", test_configuration_loading), 
        ("Database Query", test_database_query),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*50)
    print("📊 Test Results Summary:")
    print("="*50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The Twitter poster is ready to use.")
        print("\n📋 Next steps:")
        print("1. Set up Twitter API credentials in environment variables")
        print("2. Run database migration: scripts/sql/migrations/add_twitter_sent_field.sql")
        print("3. Test with: python3 entrypoints/run_twitter_poster.py")
        print("4. Enable systemd timer for automated posting")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Please fix issues before deploying.")
    
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())