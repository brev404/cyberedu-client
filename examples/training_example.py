#!/usr/bin/env python3
"""
Example script for trainings and challenge extensions.

Demonstrates:
- list_trainings, get_training, subscribe_to_training
- list_top_challenges (top N by solves/attempts/points)
- list_challenges with tag_filter
- Training deployment (start, status, wait_for)
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
TENANT = os.getenv("CYBEREDU_TENANT", "unbreakable")
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
    print(f"[OK] Authenticated as: {user_info.get('name', 'N/A')}\n")

    # List trainings
    print("=" * 70)
    print("LISTING TRAININGS")
    print("=" * 70)
    trainings = client.list_trainings()
    print(f"Found {len(trainings)} trainings\n")

    for idx, t in enumerate(trainings[:5], 1):
        title = t.get("title", "Untitled")
        slug = t.get("slug", "N/A")
        owned = "[*]" if t.get("is_owned", False) else "   "
        print(f"  {idx}. [{owned}] {title} (slug: {slug})")

    if len(trainings) > 5:
        print(f"  ... and {len(trainings) - 5} more\n")

    # Top challenges
    print("=" * 70)
    print("TOP 5 CHALLENGES (by solves)")
    print("=" * 70)
    top = client.list_top_challenges(limit=5, sort_by="solves")
    for idx, c in enumerate(top, 1):
        title = c.get("title", "Untitled")
        solves = c.get("counts", {}).get("owned", 0)
        print(f"  {idx}. {title} ({solves} solves)")

    # List challenges with tag filter (if you know a tenant tag)
    print("\n" + "=" * 70)
    print("CHALLENGES (no tag filter)")
    print("=" * 70)
    challenges = client.list_challenges()
    print(f"Total: {len(challenges)} challenges")

    # Get training details (if any exist)
    if trainings:
        first = trainings[0]
        slug = first.get("slug") or first.get("id")
        print("\n" + "=" * 70)
        print(f"TRAINING DETAILS: {first.get('title', 'N/A')}")
        print("=" * 70)
        training = client.get_training(slug)
        print(f"Title:    {training.get('title', 'N/A')}")
        print(f"Modules:  {len(training.get('modules', []))}")
        print(f"Overview: {str(training.get('overview', ''))[:80]}...")

    print("\n" + "=" * 70)
    print("Example completed!")
    print("=" * 70)
    print("\nTo subscribe, download files, or start deployment, extend this script.")
    print("MCP tools: cyberedu_list_trainings, cyberedu_get_training, etc.")

finally:
    client.close()
