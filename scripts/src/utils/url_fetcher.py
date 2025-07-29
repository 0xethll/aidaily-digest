"""
URL Content Fetching Utilities for AI Daily Digest
Handles fetching and extracting readable content from URLs
"""

import re
import time
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from readability import Document

from src.utils.logging_config import get_script_logger

logger = get_script_logger(__name__)


class URLFetcher:
    """Fetches and extracts readable content from URLs"""
    
    def __init__(
        self, 
        timeout: float = 10.0,
        max_content_length: int = 5000,
        user_agent: str = "Mozilla/5.0 (compatible; AIDigestBot/1.0)"
    ):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.user_agent = user_agent
    
    def is_image_url(self, url: str) -> bool:
        """Check if URL points to an image or non-analyzable content"""
        if not url:
            return False
        
        url_lower = url.lower().strip()
        
        # Direct image file extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp']
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True
        
        # Reddit-specific image/media URLs
        image_domains = [
            'i.redd.it',  # Direct Reddit images
            'v.redd.it',  # Reddit videos
        ]
        
        if any(domain in url_lower for domain in image_domains):
            return True
        
        # Reddit gallery URLs (usually images)
        if 'reddit.com/gallery/' in url_lower:
            return True
        
        return False
    
    def fetch_content(self, url: str) -> Optional[str]:
        """Fetch and extract readable content from URL"""
        if not url or self.is_image_url(url):
            return None
        
        try:
            # Set up headers to appear as a normal browser
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            # Fetch the URL with timeout
            response = requests.get(
                url, 
                headers=headers, 
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # Check if the response is successful
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(ct in content_type for ct in ['text/html', 'application/xhtml']):
                logger.debug(f"Skipping non-HTML content type: {content_type}")
                return None
            
            # Use readability to extract main content
            doc = Document(response.content)
            title = doc.title()
            content = doc.summary()
            
            # Parse with BeautifulSoup to clean up
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Get clean text
            clean_text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            # Limit content length
            if len(clean_text) > self.max_content_length:
                clean_text = clean_text[:self.max_content_length] + "..."
            
            # Combine title and content if both exist
            if title and title.strip():
                result = f"Article Title: {title.strip()}\n\nContent: {clean_text}"
            else:
                result = clean_text
            
            logger.debug(f"Successfully fetched content from {urlparse(url).netloc} ({len(result)} chars)")
            return result if result.strip() else None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching URL: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching URL {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching URL {url}: {e}")
            return None