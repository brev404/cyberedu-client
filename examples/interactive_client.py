#!/usr/bin/env python3
"""
Full-featured interactive CLI client for CyberEdu CTF platform.

This script provides a complete menu-driven interface for:
- Educational archive challenges (list, select, flags, files, services)
- Contest/event challenges (list contests, ranks, challenges, flags, files, services)
- User information and tenant management
- Automatic challenge unlocking
- Retry logic for flag submissions

Features:
- Loads session cookie from .env file
- Prompts for cookie if not found and saves it
- Retries with new cookie if authentication fails
- Context-aware operations (archive vs contest)
- Full challenge interaction capabilities
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv, set_key

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cyberedu_client import CyberEduClient
import httpx


def get_tenant(env_file: Path) -> str:
    """
    Get tenant from .env file or prompt user.
    
    Args:
        env_file: Path to .env file
        
    Returns:
        Tenant identifier
    """
    # Load existing .env file
    load_dotenv(env_file)
    tenant = os.getenv("CYBEREDU_TENANT")
    
    if tenant:
        return tenant
    
    # Prompt user for tenant
    print("\n" + "="*70)
    print("Tenant not configured")
    print("="*70)
    print("\nThe tenant identifier specifies which CyberEdu instance to use.")
    print("Common examples: 'cyberedu', 'training', etc.")
    print("\n" + "-"*70)
    
    tenant = input("\nEnter tenant identifier (default: cyberedu): ").strip()
    
    if not tenant:
        tenant = "cyberedu"
    
    # Save to .env file
    env_file.parent.mkdir(parents=True, exist_ok=True)
    set_key(str(env_file), "CYBEREDU_TENANT", tenant)
    print(f"\n✓ Tenant saved to {env_file}")
    
    return tenant


def get_session_cookie(env_file: Path) -> str:
    """
    Get session cookie from .env file or prompt user.
    
    Args:
        env_file: Path to .env file
        
    Returns:
        Session cookie value
    """
    # Load existing .env file
    load_dotenv(env_file)
    session_cookie = os.getenv("CYBEREDU_SESSION_COOKIE")
    
    if session_cookie:
        return session_cookie
    
    # Prompt user for cookie
    print("\n" + "="*70)
    print("Session cookie not found in .env file")
    print("="*70)
    print("\nTo get your session cookie:")
    print("  Chrome/Edge: Application tab → Cookies → app.cyber-edu.co → cyberedu_session")
    print("  Firefox: Storage tab → Cookies → app.cyber-edu.co → cyberedu_session")
    print("\n" + "-"*70)
    
    session_cookie = input("\nEnter your cyberedu_session cookie value: ").strip()
    
    if not session_cookie:
        print("ERROR: Cookie value cannot be empty")
        sys.exit(1)
    
    # Save to .env file
    env_file.parent.mkdir(parents=True, exist_ok=True)
    set_key(str(env_file), "CYBEREDU_SESSION_COOKIE", session_cookie)
    print(f"\n✓ Cookie saved to {env_file}")
    
    return session_cookie


def authenticate_with_retry(tenant: str, env_file: Path) -> CyberEduClient:
    """
    Authenticate with CyberEdu API, retrying with new cookie if it fails.
    
    Args:
        tenant: Tenant identifier
        env_file: Path to .env file
        
    Returns:
        Authenticated CyberEduClient instance
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        # Get session cookie
        session_cookie = get_session_cookie(env_file)
        
        # Initialize client
        print("\nInitializing CyberEdu client...")
        client = CyberEduClient(tenant=tenant, session_cookie=session_cookie)
        
        try:
            # Try to authenticate
            print("Checking authentication...")
            user_info = client.check_auth()
            email = user_info.get('email', 'N/A')
            name = user_info.get('name', 'N/A')
            tenants_count = len(user_info.get('tenants', []))
            print(f"✓ Authenticated! User: {name} ({email})")
            print(f"  Available tenants: {tenants_count}")
            return client
            
        except HTTPStatusError as e:
            if e.response.status_code == 401:
                retry_count += 1
                print(f"\n✗ Authentication failed (401 Unauthorized)")
                print(f"  The session cookie appears to be invalid or expired.")
                
                if retry_count < max_retries:
                    print(f"\n  Retry {retry_count}/{max_retries - 1}")
                    # Remove invalid cookie from .env
                    set_key(str(env_file), "CYBEREDU_SESSION_COOKIE", "")
                    # Will prompt for new cookie on next iteration
                else:
                    print("\n✗ Maximum retry attempts reached. Please check your cookie.")
                    client.close()
                    sys.exit(1)
            else:
                # Other HTTP errors - don't retry
                print(f"\n✗ HTTP Error {e.response.status_code}: {e.response.text}")
                client.close()
                raise
                
        except Exception as e:
            print(f"\n✗ Error during authentication: {e}")
            client.close()
            raise
    
    # Should not reach here, but just in case
    sys.exit(1)


def ensure_challenge_unlocked(client: CyberEduClient, challenge: dict) -> dict:
    """
    Ensure a challenge is unlocked (subscribed). Auto-subscribe if needed.
    
    Args:
        client: CyberEdu client instance
        challenge: Challenge dictionary
        
    Returns:
        Updated challenge dictionary (refreshed after subscription if needed)
    """
    challenge_id = challenge.get('id')
    if not challenge_id:
        return challenge
    
    is_subscribed = challenge.get('is_subscribed', False)
    
    if not is_subscribed:
        print("\n⚠ Challenge is locked. Unlocking...")
        try:
            result = client.subscribe_to_challenge(challenge_id)
            if result.get('success', False):
                print("✓ Challenge unlocked successfully!")
                # Refresh challenge data to get updated subscription status
                challenge = client.get_challenge(challenge_id)
            else:
                print("⚠ Warning: Subscription may have failed. Continuing anyway...")
        except Exception as e:
            print(f"⚠ Warning: Could not unlock challenge: {e}")
            print("Continuing anyway...")
    
    return challenge


def list_and_select_contest(client: CyberEduClient) -> dict:
    """
    List contests and let user select one.
    
    Args:
        client: CyberEdu client instance
        
    Returns:
        Selected contest dictionary or None
    """
    print("\n" + "="*70)
    print("Loading contests...")
    print("="*70)
    
    try:
        contests_data = client.list_contests()
        listed_contests = contests_data.get('listedContests', [])
        my_contests = contests_data.get('myContests', [])
        
        all_contests = listed_contests + [c for c in my_contests if c not in listed_contests]
        
        print(f"\n✓ Found {len(listed_contests)} listed contests, {len(my_contests)} my contests")
        
        if not all_contests:
            print("No contests available.")
            return None
        
        # Helper function to extract slug from URL
        def extract_slug_from_url(contest):
            """Extract slug from contest URL or subdomain."""
            url = contest.get('url', '')
            if url:
                # Extract from URL: https://unr24-individual.cyber-edu.co -> unr24-individual
                url = url.replace('https://', '').replace('http://', '')
                if '.cyber-edu.co' in url:
                    slug = url.split('.cyber-edu.co')[0]
                    return slug
            # Fallback to subdomain if URL not available
            return contest.get('subdomain', 'N/A')
        
        # Display contests
        print("\nContests:")
        for idx, contest in enumerate(all_contests, 1):
            name = contest.get('name', 'Untitled')
            status = contest.get('status', {}).get('key', 'Unknown')
            contest_type = contest.get('type', {}).get('key', 'Unknown')
            players = contest.get('players_count', 0)
            slug = extract_slug_from_url(contest)
            print(f"{idx:3}. [{status:8}] {name} ({contest_type}, {players} players, slug: {slug})")
        
        # Let user select
        while True:
            try:
                choice = input("\nEnter contest number or slug (or 'q' to quit): ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                # Try as number first
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(all_contests):
                        return all_contests[idx]
                    else:
                        print(f"Invalid number. Please enter 1-{len(all_contests)}")
                except ValueError:
                    # Try as slug - match against extracted slugs from URLs
                    matching = [
                        c for c in all_contests
                        if extract_slug_from_url(c).lower() == choice.lower()
                    ]
                    if len(matching) == 1:
                        return matching[0]
                    elif len(matching) > 1:
                        print(f"\nFound {len(matching)} matching contests:")
                        for idx, c in enumerate(matching, 1):
                            slug = extract_slug_from_url(c)
                            print(f"  {idx}. {c.get('name', 'Untitled')} (slug: {slug})")
                        continue
                    else:
                        # Try to fetch contest directly by slug
                        try:
                            contest = client.get_contest(choice)
                            if contest:
                                print(f"✓ Found contest: {contest.get('name', 'N/A')}")
                                return contest
                        except Exception as e:
                            print(f"✗ No contest found with slug '{choice}': {e}")
                            print("Please try again with a valid number or slug.")
            except KeyboardInterrupt:
                return None
    except Exception as e:
        print(f"\n✗ Error loading contests: {e}")
        return None


def show_contest_summary(contest: dict):
    """Display a summary of the contest."""
    print("\n" + "="*70)
    print("CONTEST SUMMARY")
    print("="*70)
    print(f"Name:        {contest.get('name', 'N/A')}")
    print(f"Subdomain:   {contest.get('subdomain', 'N/A')}")
    
    status = contest.get('status', {})
    status_key = status.get('key', 'Unknown') if isinstance(status, dict) else str(status)
    print(f"Status:      {status_key}")
    
    # Extract mechanism type (e.g., "jeopardy")
    mechanism = contest.get('mechanism', 'N/A')
    if isinstance(mechanism, str):
        type_display = mechanism.capitalize()
    elif isinstance(mechanism, dict):
        type_display = mechanism.get('key', mechanism.get('name', 'Unknown'))
    else:
        type_display = str(mechanism) if mechanism else 'N/A'
    print(f"Type:        {type_display}")
    
    # Extract dates from starting_at and ending_at objects
    starting_at = contest.get('starting_at', {})
    if isinstance(starting_at, dict):
        start_date = starting_at.get('date', 'N/A')
        if start_date and start_date != 'N/A':
            # Format: "2024-04-20T07:00:00.000000Z" -> "2024-04-20 07:00:00"
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                start_display = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except:
                start_display = start_date
        else:
            start_display = 'N/A'
    else:
        start_display = str(starting_at) if starting_at else 'N/A'
    
    ending_at = contest.get('ending_at', {})
    if isinstance(ending_at, dict):
        end_date = ending_at.get('date', 'N/A')
        if end_date and end_date != 'N/A':
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                end_display = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except:
                end_display = end_date
        else:
            end_display = 'N/A'
    else:
        end_display = str(ending_at) if ending_at else 'N/A'
    
    print(f"Start:       {start_display}")
    print(f"End:         {end_display}")
    
    stats = contest.get('statistics', {})
    if stats:
        print(f"Players:     {stats.get('total_players', 0)}")
        print(f"Challenges:   {stats.get('total_flags', 0)} flags")
        print(f"Attempts:     {stats.get('total_wrong_attempts', 0)} wrong attempts")
    
    challenges = contest.get('challenges', [])
    print(f"Challenges:   {len(challenges)} challenge(s)")
    
    description = contest.get('description')
    if description:
        desc_preview = description[:100].replace('\n', ' ') + "..." if len(description) > 100 else description
        print(f"Description: {desc_preview}")
    
    print("="*70)


def list_and_select_contest_challenge(client: CyberEduClient, contest_slug: str, contest: dict) -> dict:
    """
    List challenges in a contest and let user select one.
    
    Args:
        client: CyberEdu client instance
        contest_slug: Contest subdomain/slug
        contest: Contest dictionary (may already have challenges)
        
    Returns:
        Selected challenge dictionary or None
    """
    challenges = contest.get('challenges', [])
    
    if not challenges:
        print("\n✗ No challenges available in this contest.")
        return None
    
    print("\n" + "="*70)
    print(f"CHALLENGES IN CONTEST: {contest.get('name', 'N/A')}")
    print("="*70)
    
    for idx, challenge in enumerate(challenges, 1):
        title = challenge.get('title', 'Untitled')
        difficulty = challenge.get('difficulty', 'N/A')
        points = challenge.get('points', 0)
        challenge_type = challenge.get('type', 'standalone')
        owned = "✓" if challenge.get('is_owned', False) else " "
        print(f"{idx:3}. [{owned}] {title} ({difficulty}, {points} pts, {challenge_type})")
    
    # Let user select
    while True:
        try:
            choice = input("\nEnter challenge number or name (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            # Try as number first
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(challenges):
                    return challenges[idx]
                else:
                    print(f"Invalid number. Please enter 1-{len(challenges)}")
            except ValueError:
                # Try as name search
                matching = [
                    c for c in challenges
                    if choice.lower() in c.get('title', '').lower()
                ]
                if len(matching) == 1:
                    return matching[0]
                elif len(matching) > 1:
                    print(f"\nFound {len(matching)} matching challenges:")
                    for idx, c in enumerate(matching, 1):
                        print(f"  {idx}. {c.get('title', 'Untitled')}")
                    continue
                else:
                    print("No challenge found with that name. Try again.")
        except KeyboardInterrupt:
            return None


def show_contest_menu(contest: dict) -> str:
    """Display contest menu and get user choice."""
    contest_name = contest.get('name', 'Unknown Contest')
    print("\n" + "-"*70)
    print(f"CONTEST MENU: {contest_name[:50]}")
    print("-"*70)
    print("1. View contest details")
    print("2. List challenges")
    print("3. View ranks/leaderboard")
    print("4. Select challenge")
    print("5. Back to main menu")
    print("-"*70)
    
    return input("\nSelect option: ").strip().lower()


def handle_contest_ranks(client: CyberEduClient, contest_slug: str):
    """Display contest ranks/leaderboard (sorted by points descending)."""
    try:
        ranks = client.get_contest_ranks(contest_slug)
        
        if not ranks:
            print("\n✗ No ranks available for this contest.")
            return
        
        # Sort by points descending (highest first)
        # Extract points from contest_statistics.total_points
        def get_points(entry):
            stats = entry.get('contest_statistics', {})
            return stats.get('total_points', 0)
        
        sorted_ranks = sorted(ranks, key=get_points, reverse=True)
        
        print("\n" + "="*70)
        print("CONTEST RANKS/LEADERBOARD (sorted by points)")
        print("="*70)
        
        for idx, entry in enumerate(sorted_ranks, 1):
            name = entry.get('name', 'Unknown')
            stats = entry.get('contest_statistics', {})
            rank = stats.get('rank', 'N/A')
            points = stats.get('total_points', 0)
            owned = stats.get('owned_challenges_count', 0)
            accuracy = stats.get('accuracy', 0)
            
            rank_str = f"#{rank}" if rank and rank != 'N/A' else f"#{idx}"
            print(f"{idx:3}. {rank_str:6} {name:30} | Points: {points:5} | Solved: {owned:2} | Accuracy: {accuracy}%")
        
        print("="*70)
    except Exception as e:
        print(f"\n✗ Error loading ranks: {e}")


def ensure_contest_challenge_unlocked(client: CyberEduClient, contest_slug: str, challenge: dict) -> dict:
    """
    Ensure a contest challenge is unlocked (subscribed). Auto-subscribe if needed.
    
    Args:
        client: CyberEdu client instance
        contest_slug: Contest subdomain/slug
        challenge: Challenge dictionary
        
    Returns:
        Updated challenge dictionary (refreshed after subscription if needed)
    """
    challenge_id = challenge.get('id')
    if not challenge_id:
        return challenge
    
    is_subscribed = challenge.get('is_subscribed', False)
    
    if not is_subscribed:
        print("\n⚠ Challenge is locked. Unlocking...")
        try:
            result = client.subscribe_to_contest_challenge(contest_slug, challenge_id)
            if result.get('success', False):
                print("✓ Challenge unlocked successfully!")
                # Refresh challenge data to get updated subscription status
                challenge = client.get_contest_challenge(contest_slug, challenge_id)
            else:
                print("⚠ Warning: Subscription may have failed. Continuing anyway...")
        except Exception as e:
            print(f"⚠ Warning: Could not unlock challenge: {e}")
            print("Continuing anyway...")
    
    return challenge


def list_and_select_challenge(client: CyberEduClient) -> dict:
    """
    List challenges and let user select one by name.
    
    Args:
        client: CyberEdu client instance
        
    Returns:
        Selected challenge dictionary
    """
    print("\n" + "="*70)
    print("Loading challenges...")
    print("="*70)
    
    challenges = client.list_challenges()
    print(f"\n✓ Found {len(challenges)} challenges\n")
    
    if not challenges:
        print("No challenges available.")
        return None
    
    # Display challenges with index
    for idx, challenge in enumerate(challenges, 1):
        title = challenge.get('title', 'Untitled')
        category = challenge.get('category', 'N/A')
        difficulty = challenge.get('difficulty', 'N/A')
        solved = "✓" if challenge.get('solved', False) else " "
        print(f"{idx:3}. [{solved}] {title} ({category} - {difficulty})")
    
    # Let user select
    while True:
        try:
            choice = input("\nEnter challenge number or name (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            # Try as number first
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(challenges):
                    return challenges[idx]
                else:
                    print(f"Invalid number. Please enter 1-{len(challenges)}")
            except ValueError:
                # Try as name search
                matching = [
                    c for c in challenges
                    if choice.lower() in c.get('title', '').lower()
                ]
                if len(matching) == 1:
                    return matching[0]
                elif len(matching) > 1:
                    print(f"\nFound {len(matching)} matching challenges:")
                    for idx, c in enumerate(matching, 1):
                        print(f"  {idx}. {c.get('title', 'Untitled')}")
                    continue
                else:
                    print("No challenge found with that name. Try again.")
        except KeyboardInterrupt:
            return None


def show_challenge_summary(challenge: dict):
    """Display a summary of the challenge."""
    print("\n" + "="*70)
    print("CHALLENGE SUMMARY")
    print("="*70)
    print(f"Title:       {challenge.get('title', 'N/A')}")
    print(f"ID:          {challenge.get('id', 'N/A')}")
    
    # Category might be in different fields (category, tag, tags array)
    category = challenge.get('category')
    if not category:
        tags = challenge.get('tags', [])
        if tags and isinstance(tags, list) and len(tags) > 0:
            # If tags is a list of objects, get the name
            if isinstance(tags[0], dict):
                category = tags[0].get('name') or tags[0].get('slug')
            else:
                category = tags[0]
        elif challenge.get('tag'):
            category = challenge.get('tag')
    print(f"Category:    {category or 'N/A'}")
    
    print(f"Difficulty:  {challenge.get('difficulty', 'N/A')}")
    print(f"Points:      {challenge.get('points', 0)}")
    
    # Check if challenge is solved - check multiple indicators
    is_solved = challenge.get('solved', False)
    if not is_solved:
        # Check is_owned field (indicates user has solved it)
        is_solved = challenge.get('is_owned', False)
    if not is_solved:
        # Check if all flags are solved
        flags = challenge.get('flags', []) or challenge.get('questions', [])
        if flags:
            # Check if flags have 'found' or 'solved' property
            all_solved = all(
                flag.get('found', False) or flag.get('solved', False)
                for flag in flags if isinstance(flag, dict)
            )
            if all_solved:
                is_solved = True
    if not is_solved:
        # Check permissions - if submit_flag is false, might indicate solved
        permissions = challenge.get('permissions', {})
        if permissions.get('submit_flag') is False and not permissions.get('guest', True):
            is_solved = True
    
    print(f"Solved:      {'Yes ✓' if is_solved else 'No'}")
    
    # Count files - check media, files, and actions arrays (priority: media > files > actions)
    files = challenge.get('media', [])
    if not files:
        files = challenge.get('files', [])
    if not files:
        actions = challenge.get('actions', [])
        if actions:
            # Count download actions as files
            files = [
                action for action in actions
                if action.get('type') == 'download' or 'download' in action.get('action', '').lower()
            ]
            if not files:
                files = actions  # Fallback: count all actions as potential files
    print(f"Files:       {len(files)} file(s)")
    
    flags = challenge.get('flags', []) or challenge.get('questions', [])
    print(f"Flags:       {len(flags)} flag(s)")
    
    # Show description if available
    description = challenge.get('description') or challenge.get('content')
    if description:
        desc_preview = description[:100].replace('\n', ' ') + "..." if len(description) > 100 else description
        print(f"Description: {desc_preview}")
    
    # Check if challenge has a service/deployment
    # Service is available if:
    # 1. type is 'deployment' (regardless of deployment field)
    # 2. type is not 'standalone' AND deployment field exists
    challenge_type = challenge.get('type', 'standalone')
    deployment = challenge.get('deployment') or challenge.get('service')
    has_service = (challenge_type == 'deployment') or (challenge_type != 'standalone' and deployment is not None)
    
    if has_service:
        print(f"Service:     Available (type: {challenge_type})")
    else:
        print(f"Service:     Not available")
    
    print("="*70)


def show_action_menu(tenant: str) -> str:
    """Display action menu and get user choice."""
    print("\n" + "-"*70)
    print("ACTIONS")
    print("-"*70)
    print("1. Show challenge summary")
    print("2. List files")
    print("3. Download file")
    print("4. List flags/questions")
    print("5. Submit flag/answer")
    print("6. Start service")
    print("7. Get service status")
    print("8. Extend service")
    print("9. Restart service")
    print("0. Select different challenge")
    print("u. Show user info & tenants")
    print("t. Change tenant (current: {})".format(tenant))
    print("q. Back to main menu")
    print("-"*70)
    
    return input("\nSelect action: ").strip().lower()


def handle_list_files(client: CyberEduClient, challenge: dict, contest_slug: Optional[str] = None):
    """List challenge files (works for both archive and contest)."""
    challenge_id = challenge.get('id')
    
    # Try to get files from multiple possible locations
    # Priority: media > files > actions
    files = challenge.get('media', [])
    
    if not files:
        files = challenge.get('files', [])
    
    # If no files in 'files' or 'media' arrays, check 'actions' array for download actions
    if not files:
        actions = challenge.get('actions', [])
        if actions:
            # Filter actions that are download/file actions
            files = [
                action for action in actions
                if action.get('type') == 'download' or 'download' in action.get('action', '').lower()
            ]
            # If still no files, try to get all actions that might be files
            if not files and actions:
                files = actions
    
    # If still no files and we have a challenge_id, try fetching full challenge details
    if not files and challenge_id:
        try:
            if contest_slug:
                full_challenge = client.get_contest_challenge(contest_slug, challenge_id)
            else:
                full_challenge = client.get_challenge(challenge_id)
            files = full_challenge.get('media', [])
            if not files:
                files = full_challenge.get('files', [])
            if not files:
                actions = full_challenge.get('actions', [])
                if actions:
                    files = [
                        action for action in actions
                        if action.get('type') == 'download' or 'download' in action.get('action', '').lower()
                    ]
                    if not files:
                        files = actions
        except Exception as e:
            print(f"\n⚠ Warning: Could not fetch full challenge details: {e}")
    
    if not files:
        print("\n✗ No files available for this challenge.")
        return
    
    print(f"\n{'='*70}")
    print(f"FILES ({len(files)} total)")
    print("="*70)
    for idx, file_info in enumerate(files, 1):
        # Handle different field names: media uses 'file_name', files uses 'name', actions might use 'label'
        file_id = file_info.get('id') or file_info.get('file_id') or file_info.get('action_id', 'N/A')
        file_name = file_info.get('file_name') or file_info.get('name') or file_info.get('filename') or file_info.get('label', 'unknown')
        file_size = file_info.get('size', 0)
        file_type = file_info.get('type') or file_info.get('mime_type', '')
        size_str = f"{file_size:,} bytes" if file_size else "Unknown size"
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.2f} MB ({size_str})"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.2f} KB ({size_str})"
        
        print(f"{idx}. {file_name}")
        if file_type:
            print(f"   ID: {file_id}, Type: {file_type}, Size: {size_str}")
        else:
            print(f"   ID: {file_id}, Size: {size_str}")


def handle_download_file(client: CyberEduClient, challenge: dict, contest_slug: Optional[str] = None):
    """Download a challenge file (works for both archive and contest)."""
    challenge_id = challenge.get('id')
    
    # Try to get files from multiple possible locations (same logic as handle_list_files)
    # Priority: media > files > actions
    files = challenge.get('media', [])
    
    if not files:
        files = challenge.get('files', [])
    
    # If no files in 'files' or 'media' arrays, check 'actions' array for download actions
    if not files:
        actions = challenge.get('actions', [])
        if actions:
            # Filter actions that are download/file actions
            files = [
                action for action in actions
                if action.get('type') == 'download' or 'download' in action.get('action', '').lower()
            ]
            # If still no files, try to get all actions that might be files
            if not files and actions:
                files = actions
    
    # If still no files and we have a challenge_id, try fetching full challenge details
    if not files and challenge_id:
        try:
            if contest_slug:
                full_challenge = client.get_contest_challenge(contest_slug, challenge_id)
            else:
                full_challenge = client.get_challenge(challenge_id)
            files = full_challenge.get('media', [])
            if not files:
                files = full_challenge.get('files', [])
            if not files:
                actions = full_challenge.get('actions', [])
                if actions:
                    files = [
                        action for action in actions
                        if action.get('type') == 'download' or 'download' in action.get('action', '').lower()
                    ]
                    if not files:
                        files = actions
        except Exception as e:
            print(f"\n⚠ Warning: Could not fetch full challenge details: {e}")
    
    if not files:
        print("\n✗ No files available for this challenge.")
        return
    
    print("\nAvailable files:")
    for idx, file_info in enumerate(files, 1):
        file_name = file_info.get('file_name') or file_info.get('name') or file_info.get('filename') or file_info.get('label', 'unknown')
        print(f"{idx}. {file_name}")
    
    try:
        choice = int(input("\nEnter file number to download: ").strip())
        if 1 <= choice <= len(files):
            file_info = files[choice - 1]
            # Handle different field names: media uses 'id', files uses 'id', actions might use different fields
            file_id = file_info.get('id') or file_info.get('file_id') or file_info.get('action_id')
            file_name = file_info.get('file_name') or file_info.get('name') or file_info.get('filename') or file_info.get('label', 'unknown')
            
            if not file_id or file_id == 'N/A':
                print("\n✗ Error: Could not determine file ID for download.")
                return
            
            print(f"\nDownloading {file_name}...")
            if contest_slug:
                file_content = client.download_contest_file(contest_slug, challenge_id, file_id)
            else:
                file_content = client.download_file(challenge_id, file_id)
            
            # Save to current directory
            output_path = Path(file_name)
            with open(output_path, 'wb') as f:
                f.write(file_content)
            
            print(f"✓ File saved to: {output_path.absolute()}")
        else:
            print("Invalid file number.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    except Exception as e:
        print(f"\n✗ Error downloading file: {e}")


def handle_list_flags(client: CyberEduClient, challenge: dict, contest_slug: Optional[str] = None):
    """List flags/questions for the challenge (works for both archive and contest)."""
    flags = challenge.get('flags', []) or challenge.get('questions', [])
    if not flags:
        print("\n✗ No flags/questions available for this challenge.")
        return
    
    print(f"\n{'='*70}")
    print(f"FLAGS/QUESTIONS ({len(flags)} total)")
    print("="*70)
    challenge_id = challenge.get('id')
    
    for idx, flag in enumerate(flags, 1):
        flag_id = flag.get('id', 'N/A')
        flag_text = flag.get('text') or flag.get('question') or flag.get('label') or flag.get('name')
        flag_solved = flag.get('solved', False)
        
        # Always try to fetch flag details from API to get accurate solved status
        # The challenge list might not have the latest solved status
        if flag_id != 'N/A' and challenge_id:
            try:
                if contest_slug:
                    flag_details = client.get_contest_flag(contest_slug, challenge_id, flag_id)
                else:
                    flag_details = client.get_flag(challenge_id, flag_id)
                # Update flag text if missing
                if not flag_text:
                    flag_text = flag_details.get('text') or flag_details.get('question') or flag_details.get('label') or flag_details.get('name') or 'N/A'
                # Always update solved status from API response (most accurate)
                # The API uses 'found' field to indicate if flag is solved
                flag_solved = flag_details.get('found', False) or flag_details.get('solved', False)
            except Exception as e:
                # If API call fails, use the data we have
                if not flag_text:
                    flag_text = f'N/A (Error fetching: {e})'
                # Keep the solved status from the challenge data if API call failed
        
        if not flag_text:
            flag_text = 'N/A'
        
        solved = "✓ Solved" if flag_solved else "✗ Not solved"
        display_text = flag_text[:60] + "..." if len(flag_text) > 60 else flag_text
        print(f"{idx}. {display_text}")
        print(f"   ID: {flag_id}, Status: {solved}")


def handle_submit_flag(client: CyberEduClient, challenge: dict, contest_slug: Optional[str] = None):
    """Submit a flag/answer (works for both archive and contest).
    
    Returns:
        True if submission was successful, False otherwise
    """
    flags = challenge.get('flags', []) or challenge.get('questions', [])
    if not flags:
        print("\n✗ No flags/questions available for this challenge.")
        return False
    
    print("\nAvailable flags/questions:")
    challenge_id = challenge.get('id')
    
    for idx, flag in enumerate(flags, 1):
        flag_id = flag.get('id', 'N/A')
        flag_text = flag.get('text') or flag.get('question') or flag.get('label') or flag.get('name')
        
        # If flag text is missing, try to fetch it from the API
        if not flag_text and flag_id != 'N/A' and challenge_id:
            try:
                if contest_slug:
                    flag_details = client.get_contest_flag(contest_slug, challenge_id, flag_id)
                else:
                    flag_details = client.get_flag(challenge_id, flag_id)
                flag_text = flag_details.get('text') or flag_details.get('question') or flag_details.get('label') or flag_details.get('name') or 'N/A'
            except Exception:
                flag_text = 'N/A'
        
        if not flag_text:
            flag_text = 'N/A'
        
        flag_solved = flag.get('found', False) or flag.get('solved', False)
        solved = "✓" if flag_solved else " "
        display_text = flag_text[:50] + "..." if len(flag_text) > 50 else flag_text
        print(f"{idx}. [{solved}] {display_text}")
    
    try:
        choice = int(input("\nEnter flag/question number: ").strip())
        if 1 <= choice <= len(flags):
            flag_info = flags[choice - 1]
            flag_id = flag_info.get('id')
            
            flag_solved = flag_info.get('found', False) or flag_info.get('solved', False)
            if flag_solved:
                print("\n⚠ This flag/question is already solved.")
                return False
            
            # Loop to allow retries after failed submissions
            while True:
                flag_value = input("\nEnter flag/answer value (or 'q' to quit): ").strip()
                if flag_value.lower() == 'q':
                    print("Cancelled.")
                    return False
                
                if not flag_value:
                    print("Flag value cannot be empty. Please try again.")
                    continue
                
                print(f"\nSubmitting flag...")
                try:
                    if contest_slug:
                        result = client.submit_contest_flag(contest_slug, challenge['id'], flag_id, flag_value)
                    else:
                        result = client.submit_flag(challenge['id'], flag_id, flag_value)
                    
                    # Handle the response based on status
                    status = result.get('status', 'unknown')
                    solved = result.get('solved', False)
                    
                    if status == 'success' or solved:
                        print(f"\n✓ Flag submitted successfully!")
                        print(f"  Status: {status}")
                        print(f"  Solved: {'Yes ✓' if solved else 'No'}")
                        if 'message' in result:
                            print(f"  Message: {result['message']}")
                        return True  # Indicate success so challenge can be refreshed
                    elif status == 'failed':
                        print(f"\n✗ Flag submission failed.")
                        print(f"  Status: {status}")
                        print(f"  Solved: {'Yes ✓' if solved else 'No'}")
                        if 'message' in result:
                            print(f"  Message: {result['message']}")
                        
                        # Ask if user wants to retry - automatically retry unless they say 'n' or 'q'
                        retry = input("\nTry again? (press Enter to retry, 'n' to quit): ").strip().lower()
                        if retry in ('n', 'q', 'no', 'quit'):
                            break  # User doesn't want to retry
                        # Loop continues to ask for new flag value (default behavior is to retry)
                    else:
                        print(f"\nSubmission result: {result}")
                        break
                except httpx.HTTPStatusError as e:
                    # Try to parse error response if available
                    try:
                        error_body = e.response.json()
                        status = error_body.get('status', 'error')
                        solved = error_body.get('solved', False)
                        print(f"\n✗ Flag submission failed.")
                        print(f"  Status: {status}")
                        print(f"  Solved: {'Yes ✓' if solved else 'No'}")
                        if 'message' in error_body:
                            print(f"  Message: {error_body['message']}")
                        
                        # Ask if user wants to retry - automatically retry unless they say 'n' or 'q'
                        retry = input("\nTry again? (press Enter to retry, 'n' to quit): ").strip().lower()
                        if retry in ('n', 'q', 'no', 'quit'):
                            break  # User doesn't want to retry
                    except:
                        print(f"\n✗ Error submitting flag: {e}")
                        return False
        else:
            print("Invalid flag number.")
            return False
    except ValueError:
        print("Invalid input. Please enter a number.")
        return False
    except Exception as e:
        print(f"\n✗ Error submitting flag: {e}")
        return False


def handle_service_action(client: CyberEduClient, challenge: dict, action: str, contest_slug: Optional[str] = None):
    """Handle service-related actions (works for both archive and contest challenges)."""
    challenge_id = challenge['id']
    
    # Check if challenge has a service
    challenge_type = challenge.get('type', 'standalone')
    deployment = challenge.get('deployment') or challenge.get('service')
    has_service = (challenge_type == 'deployment') or (challenge_type != 'standalone' and deployment is not None)
    
    if not has_service:
        print("\n✗ This challenge does not have a service/deployment.")
        print(f"  Challenge type: {challenge_type}")
        return
    
    try:
        if action == "start":
            print("\nStarting service...")
            if contest_slug:
                result = client.start_contest_service(contest_slug, challenge_id)
            else:
                result = client.start_service(challenge_id)
            print(f"✓ Service started: {result}")
        elif action == "status":
            print("\nGetting service status...")
            if contest_slug:
                result = client.get_contest_service_status(contest_slug, challenge_id)
            else:
                result = client.get_service_status(challenge_id)
            print(f"✓ Service status: {result}")
        elif action == "extend":
            print("\nExtending service...")
            if contest_slug:
                result = client.extend_contest_service(contest_slug, challenge_id)
            else:
                result = client.extend_service(challenge_id)
            print(f"✓ Service extended: {result}")
        elif action == "restart":
            print("\nRestarting service...")
            if contest_slug:
                result = client.restart_contest_service(contest_slug, challenge_id)
            else:
                result = client.restart_service(challenge_id)
            print(f"✓ Service restarted: {result}")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def handle_show_user_info(client: CyberEduClient, current_tenant_slug: str):
    """Display user information and available tenants."""
    try:
        user_info = client.get_user_info()
        
        print("\n" + "="*70)
        print("USER INFORMATION")
        print("="*70)
        print(f"Name:        {user_info.get('name', 'N/A')}")
        print(f"Email:       {user_info.get('email', 'N/A')}")
        print(f"ID:          {user_info.get('id', 'N/A')}")
        print(f"Verified:    {'Yes ✓' if user_info.get('verified', False) else 'No'}")
        print(f"Company:     {user_info.get('company', 'N/A')}")
        print(f"Created:     {user_info.get('created_at', 'N/A')}")
        
        roles = user_info.get('roles', [])
        if roles:
            print(f"\nRoles:")
            for role in roles:
                scope = role.get('scope', 'N/A')
                title = role.get('title', role.get('name', 'N/A'))
                print(f"  - {title} (scope: {scope})")
        
        tenants = user_info.get('tenants', [])
        print(f"\nAvailable Tenants ({len(tenants)}):")
        print("-"*70)
        for idx, tenant in enumerate(tenants, 1):
            api_selected = "✓" if tenant.get('selected', False) else " "
            slug = tenant.get('slug', 'N/A')
            name = tenant.get('name', 'N/A')
            protocol = tenant.get('protocol', 'N/A')
            
            # Mark if this is the tenant currently being used by the client
            client_marker = " <-- CLIENT" if slug == current_tenant_slug else ""
            print(f"{idx:2}. [{api_selected}] {name} (slug: {slug}, protocol: {protocol}){client_marker}")
        
        # Show API's selected tenant vs client's active tenant
        api_selected_tenant = client.get_current_tenant_info()
        if api_selected_tenant:
            api_slug = api_selected_tenant.get('slug', 'N/A')
            api_name = api_selected_tenant.get('name', 'N/A')
            print(f"\nAPI Selected Tenant (from web UI): {api_name} ({api_slug})")
        
        # Find current client tenant info
        client_tenant_info = next((t for t in tenants if t.get('slug') == current_tenant_slug), None)
        if client_tenant_info:
            client_name = client_tenant_info.get('name', 'N/A')
            print(f"Client Active Tenant (in use): {client_name} ({current_tenant_slug})")
            if api_selected_tenant and api_selected_tenant.get('slug') != current_tenant_slug:
                print(f"\n⚠ Note: The checkbox (✓) shows what's selected in the web UI.")
                print(f"   The client can use any tenant regardless of the web UI selection.")
                print(f"   Use option 5 in main menu to sync with API's selected tenant.")
        
        print("="*70)
    except Exception as e:
        print(f"\n✗ Error getting user info: {e}")


def change_tenant(client: CyberEduClient, env_file: Path, current_tenant: str) -> tuple:
    """
    Handle tenant change.
    
    Returns:
        Tuple of (new_tenant, new_client) or (current_tenant, client) if cancelled
    """
    print("\n" + "="*70)
    print("Change Tenant")
    print("="*70)
    
    # Show available tenants
    try:
        tenants = client.list_tenants()
        if tenants:
            print("\nAvailable tenants:")
            for idx, t in enumerate(tenants, 1):
                selected = "✓" if t.get('selected', False) else " "
                slug = t.get('slug', 'N/A')
                name = t.get('name', 'N/A')
                print(f"{idx:2}. [{selected}] {name} (slug: {slug})")
            
            print(f"\nCurrent tenant: {current_tenant}")
            choice = input("\nEnter tenant number or slug (or 'c' to cancel): ").strip()
            
            if choice.lower() == 'c':
                print("Tenant change cancelled.")
                return current_tenant, client
            
            # Try as number first
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(tenants):
                    new_tenant = tenants[idx].get('slug', current_tenant)
                else:
                    print(f"Invalid number. Please enter 1-{len(tenants)}")
                    return current_tenant, client
            except ValueError:
                # Try as slug
                matching = [t for t in tenants if t.get('slug') == choice]
                if matching:
                    new_tenant = choice
                else:
                    # Use as-is (might be a valid slug not in list)
                    new_tenant = choice
        else:
            print("\nNo tenants available. Enter tenant slug manually.")
            new_tenant = input(f"Enter new tenant slug (current: {current_tenant}): ").strip()
            if not new_tenant:
                print("Tenant not changed.")
                return current_tenant, client
        
        if new_tenant and new_tenant != current_tenant:
            set_key(str(env_file), "CYBEREDU_TENANT", new_tenant)
            print(f"\n✓ Tenant updated to: {new_tenant}")
            print("Re-authenticating...")
            
            # Close old client
            client.close()
            
            # Create new client with new tenant
            new_client = authenticate_with_retry(new_tenant, env_file)
            print("\n✓ Tenant changed successfully.")
            return new_tenant, new_client
        else:
            return current_tenant, client
    except Exception as e:
        print(f"\n✗ Error getting tenants: {e}")
        # Fallback to manual input
        new_tenant = input(f"Enter new tenant slug (current: {current_tenant}): ").strip()
        if new_tenant and new_tenant != current_tenant:
            set_key(str(env_file), "CYBEREDU_TENANT", new_tenant)
            print(f"\n✓ Tenant updated to: {new_tenant}")
            print("Re-authenticating...")
            client.close()
            new_client = authenticate_with_retry(new_tenant, env_file)
            return new_tenant, new_client
        return current_tenant, client


def show_main_menu(tenant: str, client: CyberEduClient) -> str:
    """Display main menu and get user choice."""
    # Check if API's selected tenant differs from client's tenant
    api_selected = None
    try:
        api_selected_tenant = client.get_current_tenant_info()
        if api_selected_tenant:
            api_selected = api_selected_tenant.get('slug')
    except:
        pass
    
    print("\n" + "="*70)
    print("MAIN MENU")
    print("="*70)
    print(f"Current Tenant: {tenant}")
    if api_selected and api_selected != tenant:
        print(f"⚠ API Selected: {api_selected} (differs from client)")
    print("-"*70)
    print("ARCHIVE (Educational)")
    print("  1. List challenges")
    print("  2. Select challenge")
    print("-"*70)
    print("CONTESTS/EVENTS")
    print("  3. List contests")
    print("  4. Select contest")
    print("-"*70)
    print("  5. View user info & tenants")
    print("  6. Change tenant")
    if api_selected and api_selected != tenant:
        print("  7. Use API's selected tenant ({})".format(api_selected))
    print("q. Quit")
    print("="*70)
    
    return input("\nSelect option: ").strip().lower()


def main():
    # Find or create .env file in the examples directory
    examples_dir = Path(__file__).parent
    env_file = examples_dir / ".env"
    
    # Get tenant configuration
    tenant = get_tenant(env_file)
    
    # Authenticate (with retry logic)
    client = authenticate_with_retry(tenant, env_file)
    
    try:
        print("\n" + "="*70)
        print("CyberEdu CTF Platform - Interactive Client")
        print(f"Tenant: {tenant}")
        print("="*70)
        
        current_challenge = None
        current_contest = None
        current_contest_slug = None
        
        while True:
            # Show main menu
            main_action = show_main_menu(tenant, client)
            
            if main_action == 'q':
                print("\nExiting...")
                break
            elif main_action == '7':
                # Use API's selected tenant
                try:
                    api_selected_tenant = client.get_current_tenant_info()
                    if api_selected_tenant:
                        api_slug = api_selected_tenant.get('slug')
                        api_name = api_selected_tenant.get('name', api_slug)
                        if api_slug == tenant:
                            print(f"\n✓ Client is already using API's selected tenant: {api_name} ({api_slug})")
                        else:
                            print(f"\nSwitching to API's selected tenant: {api_name} ({api_slug})")
                            set_key(str(env_file), "CYBEREDU_TENANT", api_slug)
                            print(f"Re-authenticating with {api_slug}...")
                            client.close()
                            client = authenticate_with_retry(api_slug, env_file)
                            tenant = api_slug
                            current_challenge = None
                            current_contest = None
                            current_contest_slug = None
                            print(f"✓ Switched to {api_name} ({api_slug})")
                    else:
                        print("\n✗ No tenant is selected in the API.")
                except Exception as e:
                    print(f"\n✗ Error: {e}")
            elif main_action == '1':
                # List challenges (just show them, don't require selection)
                print("\n" + "="*70)
                print("Loading challenges...")
                print("="*70)
                challenges = client.list_challenges()
                print(f"\n✓ Found {len(challenges)} challenges\n")
                
                if challenges:
                    for idx, challenge in enumerate(challenges, 1):
                        title = challenge.get('title', 'Untitled')
                        category = challenge.get('category', 'N/A')
                        difficulty = challenge.get('difficulty', 'N/A')
                        solved = "✓" if challenge.get('solved', False) else " "
                        print(f"{idx:3}. [{solved}] {title} ({category} - {difficulty})")
                else:
                    print("No challenges available.")
            elif main_action == '2':
                # Select and work with a challenge
                current_challenge = list_and_select_challenge(client)
                if not current_challenge:
                    continue
                
                # Get full challenge details
                print(f"\nLoading challenge details...")
                current_challenge = client.get_challenge(current_challenge['id'])
                
                # Ensure challenge is unlocked before showing details
                current_challenge = ensure_challenge_unlocked(client, current_challenge)
                
                show_challenge_summary(current_challenge)
                
                # Challenge-specific actions loop
                while current_challenge:
                    action = show_action_menu(tenant)
                    
                    if action == 'q':
                        # Go back to main menu
                        current_challenge = None
                        break
                    elif action == '0':
                        # Select different challenge
                        current_challenge = None
                        break
                    elif action == 't':
                        # Change tenant (from challenge menu)
                        tenant, client = change_tenant(client, env_file, tenant)
                        current_challenge = None  # Reset challenge
                        break
                    elif action == 'u':
                        handle_show_user_info(client, tenant)
                    elif action == '1':
                        # Ensure unlocked before showing summary
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        show_challenge_summary(current_challenge)
                    elif action == '2':
                        # Ensure unlocked before listing files
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        handle_list_files(client, current_challenge, None)  # None = archive context
                    elif action == '3':
                        # Ensure unlocked before downloading files
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        handle_download_file(client, current_challenge, None)  # None = archive context
                    elif action == '4':
                        # Ensure unlocked before listing flags
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        handle_list_flags(client, current_challenge, None)  # None = archive context
                    elif action == '5':
                        # Ensure unlocked before submitting flags
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        success = handle_submit_flag(client, current_challenge, None)  # None = archive context
                        # Refresh challenge data after successful submission
                        if success:
                            print("\nRefreshing challenge data...")
                            current_challenge = client.get_challenge(current_challenge['id'])
                    elif action == '6':
                        # Ensure unlocked before service actions
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        handle_service_action(client, current_challenge, "start", None)  # None = archive context
                    elif action == '7':
                        # Ensure unlocked before service actions
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        handle_service_action(client, current_challenge, "status", None)  # None = archive context
                    elif action == '8':
                        # Ensure unlocked before service actions
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        handle_service_action(client, current_challenge, "extend", None)  # None = archive context
                    elif action == '9':
                        # Ensure unlocked before service actions
                        current_challenge = ensure_challenge_unlocked(client, current_challenge)
                        handle_service_action(client, current_challenge, "restart", None)  # None = archive context
                    else:
                        print("\n✗ Invalid action. Please try again.")
                    
                    # Refresh challenge data after actions that might change it
                    if action in ['6', '8', '9']:
                        print("\nRefreshing challenge data...")
                        current_challenge = client.get_challenge(current_challenge['id'])
            elif main_action == '3':
                # List contests
                current_contest = list_and_select_contest(client)
                if not current_contest:
                    continue
                
                # Get full contest details - extract slug from URL
                url = current_contest.get('url', '')
                if url:
                    # Extract from URL: https://unr24-individual.cyber-edu.co -> unr24-individual
                    url = url.replace('https://', '').replace('http://', '')
                    if '.cyber-edu.co' in url:
                        contest_slug = url.split('.cyber-edu.co')[0]
                    else:
                        contest_slug = url
                else:
                    # Fallback to subdomain if URL not available
                    contest_slug = current_contest.get('subdomain')
                
                if not contest_slug:
                    print("\n✗ Could not determine contest slug. Please select contest again.")
                    current_contest = None
                    continue
                
                current_contest_slug = contest_slug
                print(f"\nLoading contest details...")
                current_contest = client.get_contest(contest_slug)
                show_contest_summary(current_contest)
                
                # Contest menu loop
                while current_contest:
                    contest_action = show_contest_menu(current_contest)
                    
                    if contest_action == '5' or contest_action == 'q':
                        # Back to main menu
                        current_contest = None
                        current_contest_slug = None
                        break
                    elif contest_action == '1':
                        # View contest details
                        show_contest_summary(current_contest)
                    elif contest_action == '2':
                        # List challenges
                        challenges = current_contest.get('challenges', [])
                        if challenges:
                            print("\n" + "="*70)
                            print(f"CHALLENGES IN CONTEST: {current_contest.get('name', 'N/A')}")
                            print("="*70)
                            for idx, challenge in enumerate(challenges, 1):
                                title = challenge.get('title', 'Untitled')
                                difficulty = challenge.get('difficulty', 'N/A')
                                points = challenge.get('points', 0)
                                challenge_type = challenge.get('type', 'standalone')
                                owned = "✓" if challenge.get('is_owned', False) else " "
                                print(f"{idx:3}. [{owned}] {title} ({difficulty}, {points} pts, {challenge_type})")
                        else:
                            print("\n✗ No challenges available in this contest.")
                    elif contest_action == '3':
                        # View ranks
                        handle_contest_ranks(client, current_contest_slug)
                    elif contest_action == '4':
                        # Select challenge from contest
                        selected_challenge = list_and_select_contest_challenge(client, current_contest_slug, current_contest)
                        if not selected_challenge:
                            continue
                        
                        challenge_id = selected_challenge.get('id')
                        if not challenge_id:
                            print("\n✗ Challenge ID not found.")
                            continue
                        
                        # Get full challenge details
                        print(f"\nLoading challenge details...")
                        current_challenge = client.get_contest_challenge(current_contest_slug, challenge_id)
                        
                        # Ensure challenge is unlocked
                        current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                        
                        show_challenge_summary(current_challenge)
                        
                        # Challenge-specific actions loop (contest context)
                        while current_challenge:
                            action = show_action_menu(tenant)
                            
                            if action == 'q':
                                # Go back to contest menu
                                current_challenge = None
                                break
                            elif action == '0':
                                # Select different challenge
                                current_challenge = None
                                break
                            elif action == 't':
                                # Change tenant
                                tenant, client = change_tenant(client, env_file, tenant)
                                current_challenge = None
                                current_contest = None
                                current_contest_slug = None
                                break
                            elif action == 'u':
                                handle_show_user_info(client, tenant)
                            elif action == '1':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                show_challenge_summary(current_challenge)
                            elif action == '2':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_list_files(client, current_challenge, current_contest_slug)
                            elif action == '3':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_download_file(client, current_challenge, current_contest_slug)
                            elif action == '4':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_list_flags(client, current_challenge, current_contest_slug)
                            elif action == '5':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                success = handle_submit_flag(client, current_challenge, current_contest_slug)
                                if success:
                                    print("\nRefreshing challenge data...")
                                    current_challenge = client.get_contest_challenge(current_contest_slug, current_challenge['id'])
                            elif action == '6':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_service_action(client, current_challenge, "start", current_contest_slug)
                            elif action == '7':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_service_action(client, current_challenge, "status", current_contest_slug)
                            elif action == '8':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_service_action(client, current_challenge, "extend", current_contest_slug)
                            elif action == '9':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_service_action(client, current_challenge, "restart", current_contest_slug)
                            else:
                                print("\n✗ Invalid action. Please try again.")
                            
                            # Refresh challenge data after actions that might change it
                            if action in ['6', '8', '9']:
                                print("\nRefreshing challenge data...")
                                current_challenge = client.get_contest_challenge(current_contest_slug, current_challenge['id'])
            elif main_action == '4':
                # Select contest (same as '3' but direct selection)
                current_contest = list_and_select_contest(client)
                if not current_contest:
                    continue
                
                # Extract slug from URL
                url = current_contest.get('url', '')
                if url:
                    # Extract from URL: https://unr24-individual.cyber-edu.co -> unr24-individual
                    url = url.replace('https://', '').replace('http://', '')
                    if '.cyber-edu.co' in url:
                        contest_slug = url.split('.cyber-edu.co')[0]
                    else:
                        contest_slug = url
                else:
                    # Fallback to subdomain if URL not available
                    contest_slug = current_contest.get('subdomain')
                
                if not contest_slug:
                    print("\n✗ Could not determine contest slug.")
                    current_contest = None
                    continue
                
                current_contest_slug = contest_slug
                print(f"\nLoading contest details...")
                current_contest = client.get_contest(contest_slug)
                show_contest_summary(current_contest)
                
                # Go directly to challenge selection
                selected_challenge = list_and_select_contest_challenge(client, current_contest_slug, current_contest)
                if selected_challenge:
                    challenge_id = selected_challenge.get('id')
                    if challenge_id:
                        print(f"\nLoading challenge details...")
                        current_challenge = client.get_contest_challenge(current_contest_slug, challenge_id)
                        current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                        show_challenge_summary(current_challenge)
                        
                        # Challenge actions loop (same as above)
                        while current_challenge:
                            action = show_action_menu(tenant)
                            
                            if action == 'q':
                                current_challenge = None
                                break
                            elif action == '0':
                                current_challenge = None
                                break
                            elif action == 't':
                                tenant, client = change_tenant(client, env_file, tenant)
                                current_challenge = None
                                current_contest = None
                                current_contest_slug = None
                                break
                            elif action == 'u':
                                handle_show_user_info(client, tenant)
                            elif action == '1':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                show_challenge_summary(current_challenge)
                            elif action == '2':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_list_files(client, current_challenge, current_contest_slug)
                            elif action == '3':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_download_file(client, current_challenge, current_contest_slug)
                            elif action == '4':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_list_flags(client, current_challenge, current_contest_slug)
                            elif action == '5':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                success = handle_submit_flag(client, current_challenge, current_contest_slug)
                                if success:
                                    print("\nRefreshing challenge data...")
                                    current_challenge = client.get_contest_challenge(current_contest_slug, current_challenge['id'])
                            elif action == '6':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_service_action(client, current_challenge, "start", current_contest_slug)
                            elif action == '7':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_service_action(client, current_challenge, "status", current_contest_slug)
                            elif action == '8':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_service_action(client, current_challenge, "extend", current_contest_slug)
                            elif action == '9':
                                current_challenge = ensure_contest_challenge_unlocked(client, current_contest_slug, current_challenge)
                                handle_service_action(client, current_challenge, "restart", current_contest_slug)
                            else:
                                print("\n✗ Invalid action. Please try again.")
                            
                            if action in ['6', '8', '9']:
                                print("\nRefreshing challenge data...")
                                current_challenge = client.get_contest_challenge(current_contest_slug, current_challenge['id'])
            elif main_action == '5':
                # View user info
                handle_show_user_info(client, tenant)
            elif main_action == '6':
                # Change tenant
                tenant, client = change_tenant(client, env_file, tenant)
                current_challenge = None  # Reset challenge selection
                current_contest = None
                current_contest_slug = None
            else:
                print("\n✗ Invalid option. Please try again.")
        
        print("\n" + "="*70)
        print("Thank you for using CyberEdu Client!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    main()
