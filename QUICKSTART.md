# Quick Start Guide

## 1. Get Session Cookie

Get the `cyberedu_session` cookie from your browser:

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

## 2. Basic Usage

The example script will automatically:
- Load session cookie from `examples/.env` file
- Prompt you to enter the cookie if not found
- Save the cookie to `.env` for future use
- Retry with a new cookie if authentication fails

**Option 1: Use .env file (recommended)**

Copy the example file and add your cookie:

macOS/Linux:
```bash
git clone https://github.com/CyberEDU-Cyber-Range/cyberedu-client.git
cd cyberedu-client
python3 -m venv venv  
source venv/bin/activate
pip install -e .

cp .env.example examples/.env
# Edit examples/.env and add your CYBEREDU_SESSION_COOKIE
```

Windows (PowerShell):
```powershell
git clone https://github.com/CyberEDU-Cyber-Range/cyberedu-client.git
cd cyberedu-client
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .

copy .env.example examples\.env
# Edit examples\.env and add your CYBEREDU_SESSION_COOKIE
```

**Option 2: Let the script prompt you**

Just run the script - it will prompt for the cookie if not found:

macOS/Linux:
```bash
git clone https://github.com/CyberEDU-Cyber-Range/cyberedu-client.git
cd cyberedu-client
python3 -m venv venv  
source venv/bin/activate
pip install -e .

# Simple examples (recommended for first-time users)
python examples/archive_challenge_example.py    # Educational archive
python examples/contest_challenge_example.py    # Contests/events

# Full interactive client with menus
python examples/interactive_client.py
```

Windows (PowerShell):
```powershell
git clone https://github.com/CyberEDU-Cyber-Range/cyberedu-client.git
cd cyberedu-client
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .

python examples/archive_challenge_example.py
python examples/contest_challenge_example.py
python examples/interactive_client.py
```

The scripts will save your cookie to `examples/.env` automatically.

## 3. Use in Your Code

```python
from cyberedu_client import CyberEduClient

# Initialize with tenant and cookie
client = CyberEduClient(
    tenant="cyberedu",
    session_cookie="your_cookie_here"
)

# Check auth
user = client.check_auth()
print(f"Logged in as: {user}")

# List challenges
challenges = client.list_challenges()

# Get challenge details
challenge = client.get_challenge("challenge-id-here")

# Download file
file_content = client.download_file("challenge-id", "file-id")
with open("file", "wb") as f:
    f.write(file_content)

# Start service
service = client.start_service("challenge-id")

# Submit flag
result = client.submit_flag("challenge-id", "flag-id", "CTF{flag}")

client.close()
```

## Installation

```bash
cd cyberedu-client
pip install -e .
```

## Requirements

- Python 3.10+
- httpx library (installed automatically)
- python-dotenv library (installed automatically)

## Environment Variables

The script uses the following environment variables (in `examples/.env`):

- `CYBEREDU_TENANT` - Tenant identifier (default: "cyberedu")
- `CYBEREDU_SESSION_COOKIE` - Your session cookie from browser
