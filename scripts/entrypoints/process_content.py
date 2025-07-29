#!/usr/bin/env python3
"""
Content Processing Script
Run this script to process unprocessed Reddit posts with LLM-based analysis
"""

import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.content_processor import ContentProcessor, load_processing_config
from src.config.config_models import load_config_from_env
from src.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(
    level=logging.INFO,
    log_file='content_processing.log',
    include_console=True
).getChild(__name__)


def main():
    """Main execution function"""
    logger.info("=" * 50)
    logger.info("Starting content processing")
    logger.info("=" * 50)
    
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configurations
        logger.info("Loading configuration...")
        _, supabase_config, _ = load_config_from_env()
        processing_config = load_processing_config()
        logger.info("Configuration loaded successfully")
        logger.info(f"Model: {processing_config.model_name}")
        logger.info(f"Batch size: {processing_config.batch_size}")
        logger.info(f"Temperature: {processing_config.temperature}")
        
        # Initialize processor
        logger.info("Initializing content processor...")
        processor = ContentProcessor(supabase_config, processing_config)
        logger.info("Content processor initialized successfully")
        
        # Get current processing stats
        logger.info("Getting current processing statistics...")
        stats = processor.get_processing_stats()
        logger.info(f"Total posts: {stats.get('total_posts', 0)}")
        logger.info(f"Processed posts: {stats.get('processed_posts', 0)}")
        logger.info(f"Unprocessed posts: {stats.get('unprocessed_posts', 0)}")
        logger.info(f"Processing rate: {stats.get('processing_rate', 0)}%")
        
        # Display category breakdown if available
        if stats.get('category_breakdown'):
            logger.info("Category breakdown:")
            for category, count in sorted(stats['category_breakdown'].items()):
                logger.info(f"  {category}: {count} posts")
        
        # Process unprocessed posts
        unprocessed_count = stats.get('unprocessed_posts', 0)
        if unprocessed_count > 0:
            logger.info(f"Starting to process {unprocessed_count} unprocessed posts...")
            result_stats = processor.process_all_unprocessed(limit=50)
            
            # Log results
            logger.info("=" * 50)
            logger.info("CONTENT PROCESSING RESULTS")
            logger.info("=" * 50)
            logger.info(f"Successfully processed: {result_stats.get('processed', 0)} posts")
            logger.info(f"Failed to process: {result_stats.get('failed', 0)} posts")
            logger.info(f"Skipped (already processed): {result_stats.get('skipped', 0)} posts")
            
            # Get updated stats
            logger.info("")
            logger.info("Getting updated statistics...")
            updated_stats = processor.get_processing_stats()
            logger.info(f"New processing rate: {updated_stats.get('processing_rate', 0)}%")
            logger.info(f"Remaining unprocessed: {updated_stats.get('unprocessed_posts', 0)} posts")
            
        else:
            logger.info("No unprocessed posts found - all posts are up to date!")
        
        logger.info("=" * 50)
        logger.info("Content processing completed successfully")
        logger.info("=" * 50)
        
        return 0  # Success
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Content processing failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)