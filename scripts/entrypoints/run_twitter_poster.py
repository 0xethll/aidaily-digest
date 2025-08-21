#!/usr/bin/env python3

"""
Entrypoint for Twitter poster script
Handles automated tweeting of high-scoring Reddit posts
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import and run the main function
from src.twitter_poster import main

if __name__ == "__main__":
    main()