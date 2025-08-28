"""
Twitter API client for posting automated tweets from Reddit posts
"""

import os
import tweepy
import openai
from typing import List, Dict, Optional
from dataclasses import dataclass
from src.utils.logging_config import get_script_logger

logger = get_script_logger(__name__)


@dataclass
class TwitterConfig:
    """Configuration for Twitter API access"""
    bearer_token: str
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str


@dataclass 
class TweetThread:
    """Represents a thread of tweets"""
    tweets: List[str]
    
    def __post_init__(self):
        """Validate tweet length after initialization"""
        for i, tweet in enumerate(self.tweets):
            if len(tweet) > 280:
                raise ValueError(f"Tweet {i+1} exceeds 280 characters: {len(tweet)}")


class TwitterClient:
    """Twitter API client for posting tweets and threads"""
    
    def __init__(self, config: TwitterConfig):
        """Initialize Twitter client with authentication"""
        self.config = config
        
        # Initialize Tweepy client with OAuth 1.0a User Context
        self.client = tweepy.Client(
            bearer_token=config.bearer_token,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            access_token=config.access_token,
            access_token_secret=config.access_token_secret,
            wait_on_rate_limit=False
        )
        
        # Verify credentials
        self._verify_credentials()
    
    def _verify_credentials(self) -> None:
        """Verify Twitter API credentials are valid"""
        try:
            response = self.client.get_me()
            if response and response.data: # type: ignore
                logger.info(f"Twitter API authenticated for user: @{response.data.username}") # type: ignore
            else:
                raise Exception("Failed to retrieve user information")
        except Exception as e:
            raise ConnectionError(f"Twitter API authentication failed: {e}")
    
    def post_single_tweet(self, text: str) -> Optional[str]:
        """
        Post a single tweet
        
        Args:
            text: Tweet content (max 280 characters)
            
        Returns:
            Tweet ID if successful, None if failed
        """
        if len(text) > 280:
            raise ValueError(f"Tweet exceeds 280 characters: {len(text)}")
        
        try:
            response = self.client.create_tweet(text=text)
            if response and response.data: # type: ignore
                tweet_id = response.data['id'] # type: ignore
                logger.info(f"Successfully posted tweet: {tweet_id}")
                return tweet_id
            else:
                logger.error("Failed to post tweet - no response data")
                return None
        except tweepy.TooManyRequests:
            logger.error("Rate limit exceeded for single tweet")
            return None
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return None
    
    def post_thread(self, thread: TweetThread) -> List[Optional[str]]:
        """
        Post a thread of tweets
        
        Args:
            thread: TweetThread object containing list of tweet texts
            
        Returns:
            List of tweet IDs (None for failed tweets)
        """
        if not thread.tweets:
            logger.warning("Empty thread provided")
            return []
        
        tweet_ids = []
        previous_tweet_id = None
        
        for i, tweet_text in enumerate(thread.tweets):
            try:
                if previous_tweet_id:
                    # Reply to previous tweet in thread
                    response = self.client.create_tweet(
                        text=tweet_text,
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                else:
                    # First tweet in thread
                    response = self.client.create_tweet(text=tweet_text)
                
                if response and response.data: # type: ignore
                    tweet_id = response.data['id'] # type: ignore
                    tweet_ids.append(tweet_id)
                    previous_tweet_id = tweet_id
                    logger.info(f"Successfully posted tweet {i+1}/{len(thread.tweets)}: {tweet_id}")
                else:
                    logger.error(f"Failed to post tweet {i+1}/{len(thread.tweets)} - no response data")
                    tweet_ids.append(None)
                    break  # Stop thread if any tweet fails
                    
            except tweepy.TooManyRequests:
                logger.error(f"Rate limit exceeded on tweet {i+1}/{len(thread.tweets)}. Stopping thread.")
                tweet_ids.append(None)
                break  # Stop thread if rate limited
            except Exception as e:
                logger.error(f"Error posting tweet {i+1}/{len(thread.tweets)}: {e}")
                tweet_ids.append(None)
                break  # Stop thread if any tweet fails
        
        return tweet_ids


def load_twitter_config_from_env() -> TwitterConfig:
    """
    Load Twitter configuration from environment variables
    
    Returns:
        TwitterConfig object
        
    Raises:
        ValueError: If required environment variables are missing
    """
    config = TwitterConfig(
        bearer_token=os.getenv('TWITTER_BEARER_TOKEN') or '',
        consumer_key=os.getenv('TWITTER_CONSUMER_KEY') or '',
        consumer_secret=os.getenv('TWITTER_CONSUMER_SECRET') or '',
        access_token=os.getenv('TWITTER_ACCESS_TOKEN') or '',
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET') or ''
    )
    
    # Validate required environment variables
    required_vars = [
        config.bearer_token,
        config.consumer_key,
        config.consumer_secret,
        config.access_token,
        config.access_token_secret
    ]
    
    if not all(required_vars):
        missing = []
        if not config.bearer_token: missing.append('TWITTER_BEARER_TOKEN')
        if not config.consumer_key: missing.append('TWITTER_CONSUMER_KEY')
        if not config.consumer_secret: missing.append('TWITTER_CONSUMER_SECRET')
        if not config.access_token: missing.append('TWITTER_ACCESS_TOKEN')
        if not config.access_token_secret: missing.append('TWITTER_ACCESS_TOKEN_SECRET')
        
        raise ValueError(f"Missing required Twitter environment variables: {missing}")
    
    return config


def generate_humorous_tweet_thread(title: str, summary: str, url: str, reddit_link: str) -> TweetThread:
    """
    Generate a engaging tweet thread using OpenAI based on Reddit post content
    
    Args:
        title: Reddit post title
        summary: AI-generated summary
        url: Original article URL
        reddit_link: Reddit post permalink
        
    Returns:
        TweetThread object with AI-generated humorous tweets
    """
    client = openai.OpenAI(
        base_url="https://api.fireworks.ai/inference/v1",
        api_key=os.getenv('FIREWORKS_API_KEY'),
    )
    
    # Create the prompt for generating engaging tweet thread
    link_to_use = url if url.strip() else reddit_link
    prompt = f"""### EXAMPLE ###
Input:
- Title: "Building a SaaS in 20 Days with Claude Code"
- Summary: "The post simplifies the development process with Claude Code by planning with AI, creating essential files, and executing tasks in small chunks. It proves that even complex projects like a SaaS can be built in just 20 days with the right approach."
- URL: "https://example.com/saas-claude-code"

Desired Output:
1/2 This thread breaks down how Claude Code transforms SaaS development by planning with AI and executing in focused chunks. The results? A complete project in just 20 days. {url}
2/2 The key insight: instead of wrestling with overwhelming complexity, break everything into bite-sized tasks that AI can help execute systematically.

### END OF EXAMPLE ###

### YOUR TASK ###
Now, create an engaging Twitter thread (1-2 tweets) based on the following Reddit post.

Input:
- Title: "{title}"
- Summary: "{summary}"
- URL: "{url}"
- Reddit Link: "{reddit_link}"

Requirements:
1.  **Persona & Tone:** Focus on being informative and engaging. These are AI news and tech posts - be insightful and create curiosity.
2.  **Format:**
    - Create a thread of 1-2 tweets.
    - Number the tweets (1/n, 2/n, etc.).
    - Return only the tweet content, one tweet per line.
3.  **Content:**
    - The first tweet MUST be eye-catching and create desire to learn more, especially when the topic solves a pain point.
    - The first tweet MUST include `{link_to_use}` at the end (use URL if available, otherwise reddit_link).
    - Focus on practical insights and value.
    - Subsequent tweet should expand on key insights or implications.
4.  **Constraints:**
    - Each tweet must be under 280 characters. Remember to account for URL length, all URLs are automatically shortened to 23 characters when included in a tweet.
    - Avoid generic marketing-speak ("game-changer," "revolutionary").
    - Make it conversational and accessible.
    - Focus on the "why this matters" angle.
"""

    response = client.chat.completions.create(
        model="accounts/sentientfoundation-serverless/models/dobby-mini-unhinged-plus-llama-3-1-8b",
        messages=[
            {"role": "system", "content": "You are an expert social media manager for a top-tier AI news brand. Your goal is to create engaging, informative Twitter threads that make complex tech topics accessible and valuable to readers. Focus on practical insights and why the topic matters."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=1000
    )
    
    if response.choices and response.choices[0].message.content:
        tweet_content = response.choices[0].message.content.strip()
        tweets = [tweet.strip() for tweet in tweet_content.split('\n') if tweet.strip()]
        
        # Validate tweet lengths and adjust if needed
        validated_tweets = []
        for i, tweet in enumerate(tweets):
            if len(tweet) > 280:
                raise Exception(f"Tweet {i+1} too long ({len(tweet)} chars).")
            validated_tweets.append(tweet)

        # Only add reddit_link if it wasn't already used in the first tweet
        if not url.strip():
            # Reddit link was used in first tweet, don't repeat it
            final_tweet = """#AI #dobby

Subscribe on Telegram: https://t.me/aidaily_digest_bot

Generated by dobby model
@SentientAGI
"""
        else:
            # URL was used in first tweet, add reddit discussion link
            final_tweet = f"""#AI #dobby

Reddit discussion: {reddit_link}

Subscribe on Telegram: https://t.me/aidaily_digest_bot

Generated by dobby model
@SentientAGI
"""
        
        validated_tweets.append(final_tweet)
        
        return TweetThread(validated_tweets)
    else:
        raise Exception("No response from OpenAI")

# Alias for backward compatibility 
create_thread_from_content = generate_humorous_tweet_thread