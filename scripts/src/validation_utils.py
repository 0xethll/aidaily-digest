"""
Input validation and sanitization utilities for Reddit data
"""

import re
import html
from typing import Any, Optional


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize and validate text input
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length (optional)
        
    Returns:
        str: Sanitized text
    """
    if not text or not isinstance(text, str):
        return ""
    
    # HTML decode and strip excessive whitespace
    text = html.unescape(text.strip())
    
    # Remove potentially harmful characters but preserve most Unicode
    # Keep alphanumeric, common punctuation, and Unicode letters/digits
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Limit length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip()
        
    return text


def validate_reddit_id(reddit_id: str) -> bool:
    """
    Validate Reddit ID format
    
    Args:
        reddit_id: Reddit ID to validate
        
    Returns:
        bool: True if valid format
    """
    if not reddit_id or not isinstance(reddit_id, str):
        return False
    # Reddit IDs are typically alphanumeric, 6-7 characters
    return bool(re.match(r'^[a-zA-Z0-9]{6,7}$', reddit_id))


def validate_url(url: str) -> bool:
    """
    Basic URL validation
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid URL format
    """
    if not url or not isinstance(url, str):
        return False
    # Basic URL pattern check
    return bool(re.match(r'^https?://', url)) and len(url) <= 2048


def validate_score(score: Any) -> int:
    """
    Validate and normalize score values
    
    Args:
        score: Score value to validate
        
    Returns:
        int: Validated score within reasonable bounds
    """
    try:
        score_int = int(score)
        # Reddit scores can be negative, but let's set reasonable bounds
        return max(-100000, min(100000, score_int))
    except (ValueError, TypeError):
        return 0