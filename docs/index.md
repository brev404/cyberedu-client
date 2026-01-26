# CyberEdu Client Documentation

This documentation covers the CyberEdu Python client library internals, design decisions, and extension guidelines.

## Documentation Index

| Document | Description |
|----------|-------------|
| [Architecture](./architecture.md) | Client design, internal structure, and key abstractions |
| [Extending the Client](./extending.md) | How to add new endpoints and extend functionality |

## Quick Reference

### Installation

```bash
pip install -e .
```

### Minimal Example

```python
from cyberedu_client import CyberEduClient

with CyberEduClient(tenant="cyberedu", session_cookie="your_cookie") as client:
    # List challenges
    challenges = client.list_challenges()
    
    # Get specific challenge
    challenge = client.get_challenge("challenge-id")
    
    # Submit a flag
    result = client.submit_flag("challenge-id", "flag-id", "CTF{...}")
```

### Core Concepts

1. **Tenant-based**: All requests include a `tenant` parameter identifying the organization
2. **Session authentication**: Uses browser session cookies (`cyberedu_session`)
3. **Dual domain contexts**:
   - **Archive**: Educational challenges (`/v1/challenge/...`)
   - **Contest**: Event-based challenges (`/v1/contest/{slug}/...`)
4. **Service deployments**: Some challenges require starting a service instance

### Method Categories

| Category | Archive Methods | Contest Methods |
|----------|----------------|-----------------|
| Challenges | `list_challenges()`, `get_challenge()` | `get_contest_challenge()` |
| Flags | `get_flag()`, `submit_flag()` | `get_contest_flag()`, `submit_contest_flag()` |
| Files | `download_file()` | `download_contest_file()` |
| Services | `start_service()`, `get_service_status()` | `start_contest_service()`, `get_contest_service_status()` |

### Error Handling Pattern

```python
from httpx import HTTPStatusError

try:
    result = client.get_challenge("invalid-id")
except HTTPStatusError as e:
    if e.response.status_code == 404:
        print("Challenge not found")
    elif e.response.status_code == 401:
        print("Session expired - re-authenticate")
    else:
        print(f"API error: {e.response.status_code}")
```

## Project Structure

```
cyberedu-client/
├── src/cyberedu_client/
│   ├── __init__.py          # Package exports
│   ├── cyberedu_client.py   # Main client class
│   └── models.py            # Data models/types
├── examples/
│   ├── archive_challenge_example.py
│   ├── contest_challenge_example.py
│   └── interactive_client.py
├── docs/                     # This documentation
└── README.md                 # Usage guide
```
