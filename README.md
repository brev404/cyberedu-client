# CyberEdu Client

**Official Python client for the CyberEdu CTF platform.**

This is the official, maintained Python client library for interacting with the CyberEdu CTF platform API ([https://cyber-edu.co](https://cyber-edu.co) / [https://cyberedu.ro](https://cyberedu.ro)). It provides a comprehensive interface for managing challenges, contests, flags, files, and services on the CyberEdu platform.

## Overview

This is the **official Python client** for the CyberEdu CTF platform API. It provides a complete, well-tested interface for interacting with all aspects of the platform, allowing you to:
- **Educational Archive**: List and retrieve challenge details, download files, submit flags, manage services
- **Contests/Events**: List contests, view leaderboards, interact with contest challenges
- Download challenge files (two-step process: request UUID, then download)
- Submit flags and answers (with retry support)
- Manage challenge services (start, status, extend, restart) for both archive and contest challenges

### CyberEDU Platform Overview

CyberEDU is a cybersecurity training platform that provides hands-on labs, realistic simulations, and competitive environments. It’s designed for enterprise security teams, academic institutions, government agencies, and
individual learners.

#### Core Description

CyberEDU is a comprehensive cybersecurity training platform that provides hands-on labs, realistic simulations, and competitive environments. It's designed for enterprise security teams, academic institutions, government 
agencies, and individual learners who want to develop practical cybersecurity skills through real-world scenarios.

#### Key Differentiators

- Hands-on approach: Interactive cyber ranges where users attack and defend real infrastructure (not just videos or theory)
- MITRE ATT&CK mapping: Scenarios mapped to MITRE ATT&CK, using real malware samples (safely contained)
- Better retention: 3.5x better skill retention compared to passive learning
- Real-world scenarios: Simulates actual adversary techniques and attack patterns


#### Platform Components

1. Cyber Range — Enterprise-scale cyber warfare simulation with complex network topologies
2. Cyber Labs — 650+ hands-on labs mapped to MITRE ATT&CK, browser-based and auto-graded
3. Tournament Suite — Gamified competitions (CTFs, Red vs Blue, war games)


#### Key Statistics

- 30,000+ active users worldwide
- 650+ hands-on labs
- 1,400+ simulation profiles
- 500+ events hosted
- 45+ countries served
- 250+ hours of training content


#### Target Audiences

- Students: Career-focused training with CTF challenges and leaderboards
- Academia: Curriculum with LMS integration and auto-grading
- Enterprise: Technical hiring assessments, team training, compliance mapping
- Government: Air-gapped deployments, OT/SCADA simulation, critical infrastructure defense


#### Deployment Options

- Cloud-hosted SaaS (browser-based, no installation)
- On-premise (VMware, Proxmox, bare-metal)
- Air-gapped deployments for classified environments


## Installation

```bash
cd cyberedu-client
python3 -m venv venv  
source venv/bin/activate
pip install -e .
```

Or with development dependencies:
```bash
pip install -e ".[dev]"
```

## Authentication

The CyberEdu API uses session-based authentication via cookies:

1. **Manual Login**: Log in to the platform manually in your browser
2. **Extract Cookie**: Get the `cyberedu_session` cookie from your browser's developer tools
3. **Use Cookie**: Pass the cookie value to the `CyberEduClient` constructor

### Getting the Session Cookie

**Chrome/Edge:**
1. Open Developer Tools (F12)
2. Go to Application/Storage tab
3. Navigate to Cookies → `https://app.cyber-edu.co`
4. Find `cyberedu_session` and copy its value

**Firefox:**
1. Open Developer Tools (F12)
2. Go to Storage tab
3. Navigate to Cookies → `https://app.cyber-edu.co`
4. Find `cyberedu_session` and copy its value

## Usage

### Basic Client Usage

```python
from cyberedu_client import CyberEduClient

# Initialize client with tenant and session cookie
client = CyberEduClient(
    tenant="cyberedu",
    session_cookie="your_cyberedu_session_cookie_value"
)

# Check authentication and get user info
try:
    user_info = client.check_auth()
    print(f"Authenticated as: {user_info.get('name')} ({user_info.get('email')})")
    
    # List available tenants
    tenants = client.list_tenants()
    print(f"Available tenants: {len(tenants)}")
    for tenant in tenants:
        print(f"  - {tenant.get('name')} (slug: {tenant.get('slug')})")
except Exception as e:
    print(f"Authentication failed: {e}")

# List all challenges
challenges = client.list_challenges()
print(f"Found {len(challenges)} challenges")

# List challenges with optional filters
web_challenges = client.list_challenges(category="web")
easy_challenges = client.list_challenges(difficulty="easy")

# Get challenge details
challenge_id = "9fcc0a82-40bb-4073-9bd3-bb993823ab70"
challenge = client.get_challenge(challenge_id)
print(f"Challenge: {challenge.get('title', 'N/A')}")

# Download a file (returns bytes)
file_id = "9293"
file_content = client.download_file(challenge_id, file_id)
with open("downloaded_file", "wb") as f:
    f.write(file_content)

# Download a file directly to disk (using save_path)
result = client.download_file(challenge_id, file_id, save_path="/path/to/save/file.zip")
print(f"File saved to: {result['path']} ({result['size']} bytes)")

# Start a service (for challenges that require a running instance)
service_info = client.start_service(challenge_id)
print(f"Service started: {service_info}")

# Check service status
status = client.get_service_status(challenge_id)
print(f"Service status: {status}")

# Submit a flag
flag_id = "4454"
flag_value = "CTF{your_flag_here}"
result = client.submit_flag(challenge_id, flag_id, flag_value)
print(f"Submission result: {result}")

# Extend service time
extended = client.extend_service(challenge_id)
print(f"Service extended: {extended}")

# Restart service
restarted = client.restart_service(challenge_id)
print(f"Service restarted: {restarted}")

# Close client
client.close()
```

## Examples

The `examples/` directory contains several example scripts:

- **`archive_challenge_example.py`** - Simple example for educational archive challenges
  - Lists challenges
  - Gets challenge details
  - Shows flags and files
  - Demonstrates basic operations

- **`contest_challenge_example.py`** - Simple example for contest/event challenges
  - Lists contests
  - Gets contest details and ranks
  - Shows contest challenges
  - Demonstrates contest-specific operations

- **`interactive_client.py`** - Full-featured interactive CLI client
  - Menu-driven interface
  - Works with both archive and contest challenges
  - All features: flags, files, services, tenant management

Run the examples:

```bash
# Simple examples
python examples/archive_challenge_example.py
python examples/contest_challenge_example.py

# Full interactive client
python examples/interactive_client.py
```

### Using Context Manager

```python
with CyberEduClient(tenant="cyberedu", session_cookie="cookie_value") as client:
    challenges = client.list_challenges()
    # Client automatically closes when exiting context
```

## API Methods

### Authentication & User Info
- `check_auth()` - Verify authentication by calling SSO `/auth/user` endpoint
- `get_user_info()` - Get full user information including tenants
- `list_tenants()` - List all available tenants for the authenticated user
- `get_current_tenant_info()` - Get information about currently selected tenant

### Contests/Events
- `list_contests()` - List all available contests
- `get_contest(contest_slug)` - Get contest details
- `get_contest_ranks(contest_slug)` - Get contest leaderboard/ranks
- `get_user(user_id)` - Get user information by ID

### Challenges
- `list_challenges(difficulty=None, category=None)` - List all challenges from base endpoint
- `get_challenge(challenge_id)` - Get challenge details
- `get_challenge_difficulties()` - Get available difficulty levels
- `get_challenge_tags()` - Get available challenge tags/categories
- `subscribe_to_challenge(challenge_id)` - Subscribe to challenge notifications

### Files
- `download_file(challenge_id, file_id, save_path=None)` - Download challenge file
  - If `save_path` is provided: saves file to disk and returns `{"success": True, "path": "...", "size": ...}`
  - If `save_path` is not provided: returns file content as bytes
- `download_contest_file(contest_slug, challenge_id, file_id, save_path=None)` - Download contest challenge file (same behavior as above)

### Flags/Answers
- `get_flag(challenge_id, flag_id)` - Get flag/question information
- `submit_flag(challenge_id, flag_id, flag_value)` - Submit a flag/answer

### Services/Deployments (Archive)
- `start_service(challenge_id)` - Start challenge service
- `get_service_status(challenge_id)` - Get service status
- `extend_service(challenge_id)` - Extend service time
- `restart_service(challenge_id)` - Restart service

### Contest Services/Deployments
- `start_contest_service(contest_slug, challenge_id)` - Start challenge service within a contest
- `get_contest_service_status(contest_slug, challenge_id)` - Get service status within a contest
- `extend_contest_service(contest_slug, challenge_id)` - Extend service time within a contest
- `restart_contest_service(contest_slug, challenge_id)` - Restart service within a contest

## API Endpoints

The following endpoints are available:

### Authentication
- `GET https://sso.cyber-edu.co/auth/user` - Check authentication status (SSO endpoint)
- `GET /v1/user/{user_id}` - Get user information

### Challenges
- `GET /v1/challenge?tenant={tenant}` - List all challenges (base endpoint, contains all challenge data)
- `GET /v1/challenge/{challenge_id}?tenant={tenant}` - Get challenge details
- `GET /v1/challenge/difficulties?tenant={tenant}` - Get difficulty levels
- `GET /v1/challenge/tags?tenant={tenant}` - Get challenge tags
- `POST /v1/challenge/{challenge_id}/actions/subscribe?tenant={tenant}` - Subscribe to challenge

### Files
- `GET /v1/challenge/{challenge_id}/actions/download/{file_id}` - Download file

### Flags/Submissions
- `GET /v1/domain/app/challenge/{challenge_id}/flag/{flag_id}` - Get flag info
- `POST /v1/domain/app/challenge/{challenge_id}/submit-attempt` - Submit flag

### Services/Deployments (Archive)
- `POST /v2/governor/archive/domain/app/deployment` - Start service
- `POST /v2/governor/archive/domain/app/deployment/status` - Get service status (POST with JSON body)
- `POST /v2/governor/archive/domain/app/deployment/extend` - Extend service
- `POST /v2/governor/archive/domain/app/deployment/restart` - Restart service

### Contests/Events
- `GET /v1/contest?tenant={tenant}` - List all contests
- `GET /v1/contest/{contest_slug}?tenant={tenant}` - Get contest details
- `GET /v1/contest/{contest_slug}/ranks?tenant={tenant}` - Get contest leaderboard

### Contest Challenges
- `GET /v1/contest/{contest_slug}/challenge/{challenge_id}?governorType=event&domainIdentifier={contest_slug}&tenant={tenant}` - Get challenge details
- `GET /v1/contest/{contest_slug}/challenge/{challenge_id}/flag/{flag_id}?tenant={tenant}` - Get flag info
- `POST /v1/contest/{contest_slug}/challenge/{challenge_id}/submit-attempt?tenant={tenant}` - Submit flag
- `GET /v1/contest/{contest_slug}/challenge/{challenge_id}/actions/download/{file_id}?tenant={tenant}` - Request download (returns UUID)
- `GET /v1/contest/{contest_slug}/challenge/{challenge_id}/actions/subscribe?tenant={tenant}` - Subscribe to challenge

### Contest Services/Deployments
- `POST /v2/governor/event/domain/{contest_slug}/deployment?tenant={tenant}` - Start service (JSON body: `{"id": challenge_id}`)
- `GET /v2/governor/event/domain/{contest_slug}/deployment/status?tenant={tenant}` - Get service status (GET with JSON body: `{"id": challenge_id}`)
- `POST /v2/governor/event/domain/{contest_slug}/deployment/extend?tenant={tenant}` - Extend service (JSON body: `{"id": challenge_id}`)
- `POST /v2/governor/event/domain/{contest_slug}/deployment/restart?tenant={tenant}` - Restart service (JSON body: `{"id": challenge_id}`)

All endpoints require the `tenant` query parameter (e.g., `?tenant=cyberedu`).

## Error Handling

The client uses `httpx` which raises `httpx.HTTPStatusError` for HTTP errors:

```python
from httpx import HTTPStatusError

try:
    challenge = client.get_challenge("invalid_id")
except HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")
    print(f"Response: {e.response.text}")
```

## Notes

- Session cookies expire after some time. You may need to refresh the cookie periodically.
- The API requires CORS headers, so requests must include proper `Origin` and `Referer` headers (handled automatically by the client).
- Some endpoints may require specific permissions or challenge access.
- File downloads return binary content by default. Use the optional `save_path` parameter to save directly to disk.
- The `list_challenges()` method uses the base `/v1/challenge` endpoint which contains all challenge information. Optional filtering by `difficulty` and `category` is supported via query parameters.
- Authentication endpoint is on SSO (`sso.cyber-edu.co`) not the main API domain.

## Documentation

Additional documentation is available in the `docs/` folder:

- **[docs/index.md](docs/index.md)** - Documentation overview and quick reference
- **[docs/architecture.md](docs/architecture.md)** - Client design and internals
- **[docs/extending.md](docs/extending.md)** - How to add new endpoints and extend the client

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
ruff check src/
```

## TODO
1. Add support for A/D competitions.
2. Add support for trainings.

## License

MIT
