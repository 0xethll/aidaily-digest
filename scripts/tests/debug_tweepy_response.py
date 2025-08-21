#!/usr/bin/env python3

import os
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent))

try:
    import tweepy
    from tweepy.client import Response
    from src.twitter_client import load_twitter_config_from_env

    print(os.getenv('TWITTER_BEARER_TOKEN'))
    
    print("🔍 Debugging Tweepy Response Structure")
    print("=" * 50)
    
    # Load config if available
    try:
        config = load_twitter_config_from_env()
        
        # Initialize client
        client = tweepy.Client(
            bearer_token=config.bearer_token,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            access_token=config.access_token,
            access_token_secret=config.access_token_secret
        )
        
        print("✅ Twitter client initialized")
        
        # Test get_me() response structure
        print("\n🧪 Testing get_me() response structure:")
        try:
            response = client.get_me()
            (a, b, c, d) = response
            print(f"Response type: {type(response)}")
            print(f"Response: {response}")

            print(f"Response: {response.data.username}") # type: ignore
            
            if hasattr(response, 'data'):
                print(f"response.data type: {type(response.data)}") # type: ignore
                print(f"response.data: {response.data}") # type: ignore
                
                if hasattr(response.data, 'username'): # type: ignore
                    print(f"Username: {response.data.username}") # type: ignore
                else:
                    print("❌ No username attribute in response.data")
                    print(f"Available attributes in response.data: {dir(response.data)}") # type: ignore
            else:
                print("❌ No data attribute in response")
                print(f"Available attributes in response: {dir(response)}")
                
        except Exception as e:
            print(f"❌ Error calling get_me(): {e}")
        
        # Test create_tweet structure (without actually posting)
        print("\n🧪 Testing Response structure info:")
        print("Response should be a namedtuple with: data, includes, errors, meta")
            
    except ValueError as e:
        print(f"⚠️  Configuration issue: {e}")
        print("This is expected if Twitter API credentials are not set up.")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    
print("\n" + "=" * 50)
print("Debug complete. Set up Twitter credentials to see actual response structure.")