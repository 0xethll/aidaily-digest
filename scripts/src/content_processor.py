"""
Content Processing Module for AI Daily Digest
Handles LLM-based summarization, categorization, and keyword extraction
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import openai
from fireworks.client import Fireworks
from supabase import Client
from postgrest import CountMethod
from postgrest.exceptions import APIError as SupabaseAPIError

from src.utils.logging_config import get_script_logger
from src.utils.validation_utils import sanitize_text
from src.utils.url_fetcher import URLFetcher
from src.config.config_models import SupabaseConfig, load_config_from_env

logger = get_script_logger(__name__)


@dataclass
class ProcessingConfig:
    """Configuration for content processing"""
    fireworks_api_key: str
    model_name: str = "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new"
    max_retries: int = 3
    temperature: float = 0.1
    max_tokens: int = 1000
    batch_size: int = 10
    timeout: float = 120.0  # 2 minutes timeout
    request_delay: float = 1.0  # Delay between requests
    # URL fetching configuration
    fetch_url_content: bool = True
    url_timeout: float = 10.0  # URL fetch timeout
    max_content_length: int = 10000  # Max chars from combined content
    user_agent: str = "Mozilla/5.0 (compatible; AIDigestBot/1.0)"


class ContentProcessor:
    """Processes Reddit content using LLM for summarization, categorization, and keyword extraction"""
    
    def __init__(self, supabase_config: SupabaseConfig, processing_config: ProcessingConfig):
        self.supabase_config = supabase_config
        self.processing_config = processing_config
        
        # Initialize Fireworks client
        # self.client = Fireworks(api_key=processing_config.fireworks_api_key)

        self.client = openai.OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=processing_config.fireworks_api_key,
            timeout=processing_config.timeout
        )
        
        # Initialize Supabase client
        from supabase import create_client
        self.supabase: Client = create_client(
            supabase_config.url,
            supabase_config.key
        )
        
        # Initialize URL fetcher if enabled
        if processing_config.fetch_url_content:
            self.url_fetcher = URLFetcher(
                timeout=processing_config.url_timeout,
                max_content_length=processing_config.max_content_length,
                user_agent=processing_config.user_agent
            )
        else:
            self.url_fetcher = None
    
    def _is_image_url(self, url: str) -> bool:
        """Check if URL points to an image or non-analyzable content"""
        if self.url_fetcher:
            return self.url_fetcher.is_image_url(url)
        return False
    
    def get_unprocessed_posts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get posts that haven't been processed yet and have content or URL to analyze"""
        try:
            result = self.supabase.table('reddit_posts')\
                .select('*')\
                .is_('content_processed_at', 'null')\
                .order('created_utc', desc=True)\
                .limit(limit)\
                .execute()
            
            posts = result.data or []
            
            # Filter out posts with no analyzable content
            filtered_posts = []
            for post in posts:
                has_content = post.get('content') and post['content'].strip()
                url = post.get('url')
                has_analyzable_url = url and url.strip() and not self._is_image_url(url)
                
                # Include post if it has content OR has a non-image URL
                if has_content or has_analyzable_url:
                    filtered_posts.append(post)
                    
                if len(filtered_posts) >= limit:
                    break
            
            logger.debug(f"Filtered {len(posts)} posts down to {len(filtered_posts)} processable posts (skipped image-only posts)")
            return filtered_posts
            
        except SupabaseAPIError as e:
            logger.error(f"Database error fetching unprocessed posts: {e}")
            return []
    
    def create_processing_prompt(self, title: str, content: Optional[str] = None, url: Optional[str] = None, fetched_content: Optional[str] = None) -> str:
        """Create a structured prompt for content processing"""
        prompt = f"""You are an AI content analyst specializing in AI and technology content. Analyze the following Reddit post and provide:

1. SUMMARY: A concise 2-3 sentence summary focusing on key insights and main points
2. CATEGORY: Choose ONE category that best fits:
   - news: Breaking news, announcements, industry updates
   - discussion: Community discussions, debates, opinions
   - tutorial: How-to guides, educational content, explanations
   - question: Questions seeking help or information
   - tool: Software tools, applications, libraries
   - research: Academic papers, studies, technical research
   - showcase: Projects, demos, personal work
   - other: Content that doesn't fit other categories

3. KEYWORDS: Extract 3-7 relevant keywords/phrases (comma-separated)

POST DATA:
Title: {title}"""

        # Smart content allocation: combine both sources intelligently
        total_content_limit = self.processing_config.max_content_length
        
        if fetched_content and fetched_content.strip() and content and content.strip():
            # Both sources available: 70% fetched content, 30% post content
            fetched_limit = int(total_content_limit * 0.7)
            post_limit = int(total_content_limit * 0.3)
            
            prompt += f"\nLinked Article Content: {fetched_content[:fetched_limit]}..."
            prompt += f"\nReddit Post Content: {content[:post_limit]}..."
            
        elif fetched_content and fetched_content.strip():
            # Only fetched content available
            prompt += f"\nLinked Article Content: {fetched_content[:total_content_limit]}..."
            
        elif content and content.strip():
            # Only post content available
            prompt += f"\nPost Content: {content[:total_content_limit]}..."
        
        if url:
            prompt += f"\nSource URL: {url}"
        
        prompt += """

Respond in this exact JSON format:
{
  "summary": "Your summary here",
  "category": "category_name",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}"""
        
        return prompt
    
    def process_single_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single post using the LLM"""
        try:
            # Fetch URL content if enabled and URL exists
            fetched_content = None
            url = post.get('url')
            if self.url_fetcher and url:
                fetched_content = self.url_fetcher.fetch_content(url)
                if fetched_content:
                    logger.info(f"✅ Fetched content from URL for post: {post['title'][:50]}...")
                    logger.info(f"✅ Fetched content: {fetched_content[:500]}")
                else:
                    logger.error(f"❌ Failed to fetch external URL content for url: {url}")
                    return None
                    
            prompt = self.create_processing_prompt(
                title=post['title'],
                content=post.get('content'),
                url=url,
                fetched_content=fetched_content
            )
            
            # Add delay between requests to avoid rate limiting
            time.sleep(self.processing_config.request_delay)
            
            # Make API call to Fireworks
            response = self.client.chat.completions.create(
                model=self.processing_config.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You MUST respond with ONLY valid JSON. Do not include any explanatory text, prefixes, or comments. Start your response directly with the opening brace { and end with the closing brace }."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.processing_config.temperature,
                max_tokens=self.processing_config.max_tokens
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            if response_text is None:
                logger.error(f"API returned None content for post {post['reddit_id']}")
                return None
            
            response_text = response_text.strip()
            
            # Log the raw response for debugging
            logger.debug(f"Raw API response for post {post['reddit_id']}: {repr(response_text)}")
            
            if not response_text:
                logger.error(f"API returned empty response for post {post['reddit_id']}")
                return None
            
            # Clean up response (remove code blocks and prefix text if present)
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Remove common prefix text that the model adds
            prefixes_to_remove = [
                "Here is the analysis of the Reddit post:",
                "Here is the analysis:",
                "Analysis:",
                "Here's the analysis:",
                "The analysis is:"
            ]
            
            for prefix in prefixes_to_remove:
                if response_text.strip().startswith(prefix):
                    response_text = response_text.strip()[len(prefix):].strip()
                    break
            
            response_text = response_text.strip()
            
            # Parse JSON
            try:
                result = json.loads(response_text)
                
                # Validate required fields
                if not all(key in result for key in ['summary', 'category', 'keywords']):
                    logger.error(f"Invalid response format for post {post['reddit_id']}: missing required fields")
                    return None
                
                # Sanitize and validate data
                processed_data = {
                    'summary': sanitize_text(result['summary'], max_length=1000),
                    'category': self._validate_category(result['category']),
                    'keywords': self._process_keywords(result['keywords'])
                }
                
                logger.info(f"Successfully processed post: {post['title'][:50]}...")
                return processed_data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for post {post['reddit_id']}: {e}")
                logger.error(f"Raw response that failed to parse: {repr(response_text)}")
                logger.error(f"Response length: {len(response_text)}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing post {post['reddit_id']}: {e}")
            return None
    
    def _validate_category(self, category: str) -> str:
        """Validate and normalize category"""
        valid_categories = {
            'news', 'discussion', 'tutorial', 'question', 
            'tool', 'research', 'showcase', 'other'
        }
        
        category = category.lower().strip()
        if category in valid_categories:
            return category
        
        # Try to map common variations
        category_mapping = {
            'announcement': 'news',
            'update': 'news',
            'guide': 'tutorial',
            'howto': 'tutorial',
            'help': 'question',
            'demo': 'showcase',
            'project': 'showcase',
            'paper': 'research',
            'study': 'research'
        }
        
        return category_mapping.get(category, 'other')
    
    def _process_keywords(self, keywords: List[str]) -> List[str]:
        """Process and clean keywords"""
        if not isinstance(keywords, list):
            logger.warning(f"Keywords not a list: {keywords}")
            return []
        
        processed = []
        for keyword in keywords:
            if isinstance(keyword, str):
                # Clean and normalize keyword
                clean_keyword = re.sub(r'[^\w\s-]', '', keyword.strip().lower())
                if clean_keyword and len(clean_keyword) > 1:
                    processed.append(clean_keyword)
        
        # Limit to max 10 keywords
        return processed[:10]
    
    def update_post_with_processing(self, reddit_id: str, processed_data: Dict[str, Any]) -> bool:
        """Update a post with processed data"""
        try:
            update_data = {
                'summary': processed_data['summary'],
                'content_type': processed_data['category'],
                'keywords': processed_data['keywords'],
                'content_processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('reddit_posts')\
                .update(update_data)\
                .eq('reddit_id', reddit_id)\
                .execute()
            
            if result.data:
                logger.debug(f"Updated post {reddit_id} with processed data")
                return True
            else:
                logger.error(f"Failed to update post {reddit_id}")
                return False
                
        except SupabaseAPIError as e:
            logger.error(f"Database error updating post {reddit_id}: {e}")
            return False
    
    def process_batch(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Process a batch of posts"""
        stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for post in posts:
            try:
                # Skip if already processed
                if post.get('content_processed_at'):
                    stats['skipped'] += 1
                    continue
                
                # Process the post
                processed_data = self.process_single_post(post)
                
                if processed_data:
                    # Update database
                    if self.update_post_with_processing(post['reddit_id'], processed_data):
                        stats['processed'] += 1
                    else:
                        stats['failed'] += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Error in batch processing for post {post['reddit_id']}: {e}")
                stats['failed'] += 1
        
        return stats
    
    def process_all_unprocessed(self, limit: int = 100) -> Dict[str, int]:
        """Process all unprocessed posts in batches"""
        logger.info("Starting content processing for unprocessed posts")
        
        total_stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        batch_size = self.processing_config.batch_size
        offset = 0
        
        while offset < limit:
            # Get batch of unprocessed posts
            posts = self.get_unprocessed_posts(limit=min(batch_size, limit - offset))
            
            if not posts:
                logger.info("No more unprocessed posts found")
                break
            
            logger.info(f"Processing batch of {len(posts)} posts (offset: {offset})")
            
            # Process batch
            batch_stats = self.process_batch(posts)
            
            # Update totals
            for key in total_stats:
                total_stats[key] += batch_stats[key]
            
            logger.info(f"Batch completed: {batch_stats}")
            
            offset += len(posts)
            
            # If we got fewer posts than batch size, we're done
            if len(posts) < batch_size:
                break
        
        logger.info(f"Content processing completed. Final stats: {total_stats}")
        return total_stats
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about processed content"""
        try:
            # Total posts
            total_result = self.supabase.table('reddit_posts')\
                .select('reddit_id', count=CountMethod.exact)\
                .execute()
            total_posts = total_result.count or 0
            
            # Processed posts
            processed_result = self.supabase.table('reddit_posts')\
                .select('reddit_id', count=CountMethod.exact)\
                .not_.is_('content_processed_at', 'null')\
                .execute()
            processed_posts = processed_result.count or 0
            
            # Category breakdown
            category_result = self.supabase.table('reddit_posts')\
                .select('content_type')\
                .not_.is_('content_type', 'null')\
                .execute()
            
            category_counts = {}
            for post in category_result.data or []:
                category = post['content_type']
                category_counts[category] = category_counts.get(category, 0) + 1
            
            return {
                'total_posts': total_posts,
                'processed_posts': processed_posts,
                'unprocessed_posts': total_posts - processed_posts,
                'processing_rate': round((processed_posts / total_posts * 100), 2) if total_posts > 0 else 0,
                'category_breakdown': category_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}


def load_processing_config() -> ProcessingConfig:
    """Load processing configuration from environment"""
    fireworks_api_key = os.getenv('FIREWORKS_API_KEY')
    if not fireworks_api_key:
        raise ValueError("FIREWORKS_API_KEY environment variable is required")
    
    return ProcessingConfig(
        fireworks_api_key=fireworks_api_key,
        model_name=os.getenv('FIREWORKS_MODEL', 'accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new'),
        temperature=float(os.getenv('PROCESSING_TEMPERATURE', '0.1')),
        max_tokens=int(os.getenv('PROCESSING_MAX_TOKENS', '1000')),
        batch_size=int(os.getenv('PROCESSING_BATCH_SIZE', '5')),  # Reduced batch size
        timeout=float(os.getenv('PROCESSING_TIMEOUT', '120.0')),
        request_delay=float(os.getenv('PROCESSING_REQUEST_DELAY', '2.0')),  # 2 second delay
        # URL fetching config
        fetch_url_content=os.getenv('FETCH_URL_CONTENT', 'true').lower() == 'true',
        url_timeout=float(os.getenv('URL_TIMEOUT', '10.0')),
        max_content_length=int(os.getenv('MAX_CONTENT_LENGTH', '10000')),
        user_agent=os.getenv('USER_AGENT', 'Mozilla/5.0 (compatible; AIDigestBot/1.0)')
    )


def main():
    """Main function for testing the content processor"""
    try:
        # Load configurations
        _, supabase_config, _ = load_config_from_env()
        processing_config = load_processing_config()
        
        # Initialize processor
        processor = ContentProcessor(supabase_config, processing_config)
        
        # Get current stats
        stats = processor.get_processing_stats()
        print(f"Current processing stats: {json.dumps(stats, indent=2)}")
        
        # Process unprocessed posts
        if stats.get('unprocessed_posts', 0) > 0:
            result_stats = processor.process_all_unprocessed(limit=50)
            print(f"Processing results: {json.dumps(result_stats, indent=2)}")
            
            # Get updated stats
            updated_stats = processor.get_processing_stats()
            print(f"Updated stats: {json.dumps(updated_stats, indent=2)}")
        else:
            print("No unprocessed posts found")
        
    except Exception as e:
        logger.error(f"Failed to run content processor: {e}")
        raise


if __name__ == "__main__":
    main()