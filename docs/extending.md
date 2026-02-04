# Extending the Client

Guidelines for adding new API endpoints and functionality.

## Adding a New Endpoint

### Step 1: Identify the API Pattern

Use browser dev tools to capture the request:
- Open Network tab, filter by XHR/Fetch
- Perform the action on `app.cyber-edu.co`
- Note: method, path, query params, headers, body format

### Step 2: Implement the Method

Use `_make_request()` for standard endpoints:

```python
def get_new_resource(self, resource_id: str) -> Dict[str, Any]:
    """
    Get a new resource by ID.
    
    Args:
        resource_id: The resource identifier
        
    Returns:
        Resource data dictionary
    """
    response = self._make_request('GET', f'/v1/resource/{resource_id}')
    response.raise_for_status()
    return response.json()
```

### Step 3: Handle Special Cases

**For endpoints needing custom headers or body formats:**

```python
def submit_special_form(self, challenge_id: str, value: str) -> Dict[str, Any]:
    """Submit data using form encoding (not JSON)."""
    # Use httpx directly for non-JSON bodies
    response = self.client.post(
        f'{self.BASE_URL}/v1/special/submit',
        params={'tenant': self.tenant},
        data={'id': challenge_id, 'value': value},  # form data, not json
        headers=self._build_request_headers(),
    )
    response.raise_for_status()
    return response.json()
```

**For contest-scoped endpoints:**

```python
def get_contest_resource(self, contest_slug: str, resource_id: str) -> Dict[str, Any]:
    """Get resource within a contest context."""
    params = {
        'governorType': 'event',
        'domainIdentifier': contest_slug,
    }
    response = self._make_request(
        'GET',
        f'/v1/contest/{contest_slug}/resource/{resource_id}',
        params=params
    )
    response.raise_for_status()
    return response.json()
```

## Adding Data Models

Add to `models.py` for complex response structures:

```python
@dataclass
class NewResource:
    """Represents a new resource type."""
    id: str
    name: str
    status: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NewResource':
        """Create from API response dictionary."""
        return cls(
            id=data['id'],
            name=data.get('name', ''),
            status=data.get('status', 'unknown'),
            created_at=datetime.fromisoformat(data['created_at']) 
                       if data.get('created_at') else None,
        )
```

Export in `__init__.py`:

```python
from .models import NewResource
__all__ = [..., 'NewResource']
```

## Common Patterns

### Pattern: Two-Step Operations

Some operations (like file download) require two API calls:

```python
def complex_operation(self, resource_id: str) -> Dict[str, Any]:
    """Operation requiring two API calls."""
    # Step 1: Initiate
    init_response = self._make_request('POST', f'/v1/resource/{resource_id}/init')
    init_response.raise_for_status()
    token = init_response.json().get('data', {}).get('token')
    
    # Step 2: Complete
    complete_response = self._make_request('GET', f'/v1/resource/complete/{token}')
    complete_response.raise_for_status()
    return complete_response.json()
```

### Pattern: Polling for Status

For async operations, poll until complete:

```python
import time

def wait_for_service(self, challenge_id: str, timeout: int = 120) -> Dict[str, Any]:
    """Wait for service to become ready."""
    start = time.time()
    while time.time() - start < timeout:
        status = self.get_service_status(challenge_id)
        state = status.get('data', {}).get('status')
        
        if state == 'running':
            return status
        elif state == 'error':
            raise RuntimeError("Service failed. Check get_service_status for details.")
        
        time.sleep(3)
    
    raise TimeoutError(f"Service not ready after {timeout}s")
```

### Pattern: Handling Expected 4xx Responses

When 4xx is expected (like wrong flag):

```python
def submit_with_expected_failure(self, ...) -> Dict[str, Any]:
    """Submit where 400 is a valid response."""
    response = self.client.post(...)
    
    # 400 is expected for wrong answer
    if response.status_code == 400:
        return response.json()  # Contains status info
    
    # Other errors are unexpected
    response.raise_for_status()
    return response.json()
```

## Testing New Endpoints

Add a quick test script in `examples/`:

```python
#!/usr/bin/env python3
"""Test new endpoint."""
from cyberedu_client import CyberEduClient

client = CyberEduClient(tenant="cyberedu", session_cookie="...")

# Test the new method
result = client.get_new_resource("test-id")
print(f"Result: {result}")

client.close()
```

## Checklist for New Endpoints

Compliance tests in `tests/test_compliance.py` verify these items. See `tests/COMPLIANCE_MAPPING.md`.

- [ ] Captured actual API request from browser
- [ ] Method has docstring with Args/Returns
- [ ] Uses `_make_request()` or explains why not
- [ ] Handles expected error codes (like 400 for wrong flags)
- [ ] Returns dict (not custom objects) for MCP compatibility
- [ ] Contest variant added if applicable
- [ ] Added to README.md API methods list
- [ ] Tested against real API
