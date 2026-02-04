# Client Architecture

This document explains the internal design of the CyberEdu client.

## Design Principles

1. **Stateless methods**: Each method is self-contained; no implicit state between calls
2. **Dict-based returns**: All methods return JSON-serializable dictionaries for MCP/LLM compatibility
3. **Explicit error handling**: HTTP errors are raised, not silently handled
4. **Single HTTP client**: Uses one `httpx.Client` instance for connection pooling

## Class Structure

```
CyberEduClient
├── Configuration
│   ├── tenant: str              # Organization identifier
│   ├── session_cookie: str      # Authentication token
│   ├── BASE_URL: str            # API endpoint (api.cyber-edu.co)
│   └── SSO_BASE_URL: str        # Auth endpoint (sso.cyber-edu.co)
│
├── Internal Helpers
│   ├── _build_request_headers()  # Build request headers with auth
│   ├── _make_request()          # Execute API request with tenant param
│   ├── _parse_download_uuid_from_response()  # Parse file download responses
│   ├── _parse_flag_submission_response()     # Handle 400 status for wrong flags
│   └── _save_downloaded_file()  # Write bytes to disk (uses _resolve_save_path, _write_file_to_disk)
│
└── Public Methods (grouped by domain)
    ├── Authentication & User
    ├── Archive Challenges
    ├── Archive Operations (flags, files, services)
    ├── Contest/Events
    └── Contest Operations (flags, files, services)
```

## Request Flow

All API requests flow through `_make_request()`:

```
Public Method
    │
    ▼
_make_request(method, path, params, json_data)
    │
    ├─► Adds tenant to query params
    ├─► Adds session cookie to headers via _build_request_headers()
    │
    ▼
httpx.Client.request()
    │
    ▼
httpx.Response (returned to caller)
```

### The `_make_request` Helper

```python
def _make_request(
    self,
    method: str,           # GET, POST, etc.
    path: str,             # API path like '/v1/challenge'
    params: Dict = None,   # Query params (tenant added automatically)
    json_data: Dict = None,# JSON body
    data: Dict = None,     # Form data
    headers: Dict = None,  # Additional headers
) -> httpx.Response:
```

This centralizes:
- Tenant injection into all requests
- Session cookie handling
- Consistent error propagation

## Authentication Flow

```
1. User logs in via browser at app.cyber-edu.co
2. Browser receives cyberedu_session cookie
3. User extracts cookie from dev tools
4. Client sends cookie with every request
5. Auth verification: GET sso.cyber-edu.co/auth/user
```

Note: Auth endpoint is on SSO domain, not API domain.

## Dual API Patterns

The client handles two distinct contexts:

### Archive Challenges (Educational)

- Base path: `/v1/challenge/...`
- Services: `/v2/governor/archive/domain/app/deployment/...`
- Single-tenant, standalone challenges

### Contest Challenges (Events)

- Base path: `/v1/contest/{slug}/...`
- Services: `/v2/governor/event/domain/{slug}/deployment/...`
- Requires `governorType=event` and `domainIdentifier={slug}` params
- Time-limited, competition context

## File Download Protocol

CyberEdu uses a two-step download process:

```
Step 1: Request download token
    GET /v1/challenge/{id}/actions/download/{file_id}
    Response: { "data": { "uuid": "abc-123-..." } }

Step 2: Download actual file
    GET /v1/download/{uuid}
    Response: Binary file content
```

This is handled internally by `download_file()` and `download_contest_file()`.

## Flag Submission Handling

The API returns HTTP 400 for incorrect flags (expected behavior, not error):

```python
def _parse_flag_submission_response(self, http_response):
    # 400 = wrong flag (normal), parse body for status
    # Other 4xx/5xx = actual error, raise exception
    if http_response.status_code == 400:
        return http_response.json()  # {"status": "failed", ...}
    http_response.raise_for_status()
    return http_response.json()
```

## Thread Safety

The client uses `httpx.Client` which is thread-safe for concurrent requests. However:
- Avoid modifying `session_cookie` or `tenant` during concurrent use
- Create separate client instances for different tenants/sessions

## Context Manager Support

```python
# Automatic cleanup
with CyberEduClient(...) as client:
    # Use client
    pass  # client.close() called automatically

# Manual cleanup
client = CyberEduClient(...)
try:
    # Use client
finally:
    client.close()
```
