#!/usr/bin/env python3
"""
Simple example script for interacting with contest/event challenges.

This script demonstrates basic operations:
- List contests
- Get contest details
- List contest challenges
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

def extract_slug_from_url(contest):
    """Extract slug from contest URL."""
    url = contest.get('url', '')
    if url:
        url = url.replace('https://', '').replace('http://', '')
        if '.cyber-edu.co' in url:
            return url.split('.cyber-edu.co')[0]
    return contest.get('subdomain', 'N/A')

try:
    # Verify authentication
    print("Checking authentication...")
    user_info = client.check_auth()
    print(f"✓ Authenticated as: {user_info.get('name', 'N/A')}\n")
    
    # List contests
    print("=" * 70)
    print("LISTING CONTESTS")
    print("=" * 70)
    contests_data = client.list_contests()
    listed_contests = contests_data.get('listedContests', [])
    my_contests = contests_data.get('myContests', [])
    
    all_contests = listed_contests + [c for c in my_contests if c not in listed_contests]
    print(f"Found {len(listed_contests)} listed contests, {len(my_contests)} my contests\n")
    
    # Show first 5 contests
    for idx, contest in enumerate(all_contests[:5], 1):
        name = contest.get('name', 'Untitled')
        status = contest.get('status', {}).get('key', 'Unknown') if isinstance(contest.get('status'), dict) else 'Unknown'
        slug = extract_slug_from_url(contest)
        print(f"{idx}. [{status:8}] {name} (slug: {slug})")
    
    if len(all_contests) > 5:
        print(f"... and {len(all_contests) - 5} more\n")
    
    # Get details of first contest
    if all_contests:
        first_contest = all_contests[0]
        contest_slug = extract_slug_from_url(first_contest)
        
        if contest_slug and contest_slug != 'N/A':
            print("=" * 70)
            print(f"CONTEST DETAILS: {first_contest.get('name', 'N/A')}")
            print("=" * 70)
            
            # Get full contest details
            contest = client.get_contest(contest_slug)
            print(f"Name:        {contest.get('name', 'N/A')}")
            print(f"Subdomain:   {contest.get('subdomain', 'N/A')}")
            
            mechanism = contest.get('mechanism', 'N/A')
            if isinstance(mechanism, str):
                type_display = mechanism.capitalize()
            else:
                type_display = str(mechanism)
            print(f"Type:        {type_display}")
            
            stats = contest.get('statistics', {})
            if stats:
                print(f"Players:     {stats.get('total_players', 0)}")
                print(f"Challenges:   {stats.get('total_flags', 0)} flags")
            
            # List challenges in contest
            challenges = contest.get('challenges', [])
            if challenges:
                print(f"\nChallenges ({len(challenges)}):")
                for idx, challenge in enumerate(challenges[:5], 1):
                    title = challenge.get('title', 'Untitled')
                    difficulty = challenge.get('difficulty', 'N/A')
                    points = challenge.get('points', 0)
                    owned = "✓" if challenge.get('is_owned', False) else " "
                    print(f"  {idx}. [{owned}] {title} ({difficulty}, {points} pts)")
                
                if len(challenges) > 5:
                    print(f"  ... and {len(challenges) - 5} more")
                
                # Get details of first challenge
                first_challenge = challenges[0]
                challenge_id = first_challenge.get('id')
                
                if challenge_id:
                    print("\n" + "=" * 70)
                    print(f"CHALLENGE DETAILS: {first_challenge.get('title', 'N/A')}")
                    print("=" * 70)
                    
                    # Get full challenge details
                    challenge = client.get_contest_challenge(contest_slug, challenge_id)
                    print(f"Title:       {challenge.get('title', 'N/A')}")
                    print(f"Difficulty:  {challenge.get('difficulty', 'N/A')}")
                    print(f"Points:      {challenge.get('points', 0)}")
                    
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
                        # status = client.get_contest_service_status(contest_slug, challenge_id)
                        # print(f"Service status: {status}")
                    else:
                        print(f"\nService: Not available")
            
            # Get contest ranks
            print("\n" + "=" * 70)
            print("CONTEST RANKS (Top 5)")
            print("=" * 70)
            ranks = client.get_contest_ranks(contest_slug)
            sorted_ranks = sorted(ranks, key=lambda e: e.get('contest_statistics', {}).get('total_points', 0), reverse=True)
            
            for idx, entry in enumerate(sorted_ranks[:5], 1):
                name = entry.get('name', 'Unknown')
                stats = entry.get('contest_statistics', {})
                points = stats.get('total_points', 0)
                owned = stats.get('owned_challenges_count', 0)
                print(f"{idx}. {name:30} | Points: {points:5} | Solved: {owned:2}")
        
        print("\n" + "=" * 70)
        print("Example operations completed!")
        print("=" * 70)
        print("\nTo interact with contests, use the interactive_client.py script")
        print("or extend this script with your own logic.")

finally:
    client.close()
