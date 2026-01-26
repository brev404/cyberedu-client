#!/usr/bin/env python3
"""
Simple example script for interacting with educational archive challenges.

This script demonstrates basic operations:
- List challenges
- Get challenge details
- List flags
- Submit a flag
- Download files
- Manage services
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cyberedu_client import CyberEduClient

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# Configuration
TENANT = os.getenv("CYBEREDU_TENANT", "cyberedu")
SESSION_COOKIE = os.getenv("CYBEREDU_SESSION_COOKIE")

if not SESSION_COOKIE:
    print("Error: CYBEREDU_SESSION_COOKIE not set in .env file")
    print("Please set it in examples/.env")
    sys.exit(1)

# Create client
client = CyberEduClient(tenant=TENANT, session_cookie=SESSION_COOKIE)

try:
    # Verify authentication
    print("Checking authentication...")
    user_info = client.check_auth()
    print(f"✓ Authenticated as: {user_info.get('name', 'N/A')}\n")
    
    # List challenges
    print("=" * 70)
    print("LISTING CHALLENGES")
    print("=" * 70)
    challenges = client.list_challenges()
    print(f"Found {len(challenges)} challenges\n")
    
    # Show first 5 challenges
    for idx, challenge in enumerate(challenges[:5], 1):
        title = challenge.get('title', 'Untitled')
        difficulty = challenge.get('difficulty', 'N/A')
        solved = "✓" if challenge.get('solved', False) else " "
        print(f"{idx}. [{solved}] {title} ({difficulty})")
    
    if len(challenges) > 5:
        print(f"... and {len(challenges) - 5} more\n")
    
    # Get details of first challenge
    if challenges:
        first_challenge = challenges[0]
        challenge_id = first_challenge.get('id')
        
        print("=" * 70)
        print(f"CHALLENGE DETAILS: {first_challenge.get('title', 'N/A')}")
        print("=" * 70)
        
        # Get full challenge details
        challenge = client.get_challenge(challenge_id)
        print(f"Title:       {challenge.get('title', 'N/A')}")
        print(f"Difficulty:  {challenge.get('difficulty', 'N/A')}")
        print(f"Points:      {challenge.get('points', 0)}")
        print(f"Description: {challenge.get('description', 'N/A')[:100]}...")
        
        # List flags
        flags = challenge.get('flags', []) or challenge.get('questions', [])
        if flags:
            print(f"\nFlags ({len(flags)}):")
            for idx, flag in enumerate(flags, 1):
                flag_text = flag.get('text') or flag.get('question', 'N/A')
                solved = "✓" if flag.get('found', False) or flag.get('solved', False) else " "
                print(f"  {idx}. [{solved}] {flag_text[:50]}...")
        
        # List files
        files = challenge.get('media', []) or challenge.get('files', [])
        if files:
            print(f"\nFiles ({len(files)}):")
            for idx, file_info in enumerate(files, 1):
                file_name = file_info.get('file_name') or file_info.get('name', 'N/A')
                print(f"  {idx}. {file_name}")
        
        # Check service availability
        challenge_type = challenge.get('type', 'standalone')
        deployment = challenge.get('deployment') or challenge.get('service')
        has_service = (challenge_type == 'deployment') or (challenge_type != 'standalone' and deployment is not None)
        
        if has_service:
            print(f"\nService: Available (type: {challenge_type})")
            # Example: Get service status
            # status = client.get_service_status(challenge_id)
            # print(f"Service status: {status}")
        else:
            print(f"\nService: Not available")
        
        print("\n" + "=" * 70)
        print("Example operations completed!")
        print("=" * 70)
        print("\nTo interact with challenges, use the interactive_client.py script")
        print("or extend this script with your own logic.")

finally:
    client.close()
