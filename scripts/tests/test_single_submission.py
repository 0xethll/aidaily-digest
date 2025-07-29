#!/usr/bin/env python3
"""
Test Content Processing for Specific Reddit Submission

Usage:
    python test_single_submission.py <reddit_id> [--dry-run]

Examples:
    python test_single_submission.py 1abc2def3
    python test_single_submission.py 1abc2def3 --dry-run
"""

import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import json

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.content_processor import ContentProcessor, load_processing_config
from src.config.config_models import load_config_from_env
from src.utils.logging_config import setup_logging
import logging


def main():
    parser = argparse.ArgumentParser(description='Test content processing for a specific Reddit submission')
    parser.add_argument('reddit_id', help='Reddit ID of the submission to process')
    parser.add_argument('--dry-run', action='store_true', help='Process but do not update database')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(level=log_level)
    
    try:
        # Load configuration
        _, supabase_config, _ = load_config_from_env()
        processing_config = load_processing_config()
        
        # Initialize content processor
        processor = ContentProcessor(supabase_config, processing_config)
        
        print(f"🔍 Looking for Reddit submission: {args.reddit_id}")
        
        # Get the post from database
        result = processor.supabase.table('reddit_posts')\
            .select('*')\
            .eq('reddit_id', args.reddit_id)\
            .execute()
        
        if not result.data:
            print(f"❌ No post found with reddit_id: {args.reddit_id}")
            print("💡 Make sure the post exists in the reddit_posts table")
            return 1
        
        post = result.data[0]
        print(f"✅ Found post: {post.get('title', 'No title')[:80]}...")
        print(f"📝 Content length: {len(post.get('content', '') if post.get('content', '') else '')} characters")
        print(f"🏷️  Current processed status: {'✅ Processed' if post.get('content_processed_at') else '❌ Not processed'}")
        
        if post.get('content_processed_at') and not args.dry_run:
            response = input("⚠️  Post already processed. Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return 0
        
        print(f"\n🚀 Processing content...")
        
        # Process the post using existing method
        processed_data = processor.process_single_post(post)
        
        if not processed_data:
            print("❌ Failed to process content")
            return 1
        
        print(f"\n✅ Content processing completed!")
        print(f"📊 Results:")
        print(f"   Summary: {processed_data.get('summary', 'N/A')[:100]}...")
        print(f"   Content Type: {processed_data.get('content_type', 'N/A')}")
        print(f"   Keywords: {', '.join(processed_data.get('keywords', []))}")
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN - Results not saved to database")
            print(f"\nFull processed data:")
            print(json.dumps(processed_data, indent=2, default=str))
        else:
            print(f"\n💾 Updating database...")
            success = processor.update_post_with_processing(args.reddit_id, processed_data)
            
            if success:
                print(f"✅ Database updated successfully!")
            else:
                print(f"❌ Failed to update database")
                return 1
        
        print(f"\n🎉 Test completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error testing submission {args.reddit_id}: {e}")
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())