#!/usr/bin/env python3
"""
Test script for Dobby model integration
"""

import os
import json
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

def test_dobby_model():
    """Test the Dobby model with a sample Reddit post"""
    
    # Check if API key is available
    api_key = os.getenv('FIREWORKS_API_KEY')
    if not api_key:
        print("❌ FIREWORKS_API_KEY not found in environment")
        return False
    
    # Initialize OpenAI client for Fireworks
    client = openai.OpenAI(
        base_url="https://api.fireworks.ai/inference/v1",
        api_key=api_key
    )
    
    # Test prompt
    test_title = "Claude 3.5 Sonnet now supports computer use in public beta"
    test_content = """Anthropic has announced that Claude 3.5 Sonnet can now use computers in a limited public beta. This new capability allows Claude to interact with computer interfaces by viewing screens, moving cursors, clicking buttons, and typing text. The feature is designed to help with tasks like using software, browsing the web, and following complex multi-step instructions."""
    
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
Title: {test_title}
Content: {test_content}

Respond in this exact JSON format:
{{
  "summary": "Your summary here",
  "category": "category_name",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}"""
    
    try:
        print("🔄 Testing Dobby model...")
        
        response = client.chat.completions.create(
            model="accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant that analyzes content and responds only in valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        print("✅ Model response received:")
        print(f"Raw response: {response_text}")
        
        # Try to parse JSON
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
            
        try:
            parsed = json.loads(response_text)
            print("\n🎉 Successfully parsed JSON:")
            print(json.dumps(parsed, indent=2))
            
            # Validate structure
            required_fields = ['summary', 'category', 'keywords']
            if all(field in parsed for field in required_fields):
                print("\n✅ All required fields present")
                return True
            else:
                print(f"\n❌ Missing required fields: {[f for f in required_fields if f not in parsed]}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON parsing error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing model: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Dobby Model Integration")
    print("=" * 50)
    
    success = test_dobby_model()
    
    if success:
        print("\n🎉 Dobby model test completed successfully!")
        print("You can now run the content processor.")
    else:
        print("\n❌ Dobby model test failed.")
        print("Please check your FIREWORKS_API_KEY and try again.")