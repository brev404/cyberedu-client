"""
Official CyberEdu API Client.

This module provides the official Python client for interacting with the CyberEdu CTF platform API.
Authentication is done via session cookie (cyberedu_session) obtained from manual login.

This is the official, maintained client library for the CyberEdu platform, designed to be:
- Stateless and thread-safe
- Well-typed for AI/LLM integration
- Compatible with MCP (Model Context Protocol) servers
- Easy to extend and maintain
- Production-ready and fully tested
"""

from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import httpx


class CyberEduClient:
    """
    Official client for interacting with the CyberEdu CTF platform API.
    
    This is the official Python client library for the CyberEdu platform, providing
    a comprehensive interface for all platform features including challenges, contests,
    flags, files, and services.
    
    This client is designed to be:
    - Stateless: Each method call is independent
    - Type-safe: All methods have type hints
    - MCP-ready: Can be easily integrated into MCP servers
    - AI-friendly: Clear method names and structured returns
    - Production-ready: Fully tested and maintained
    
    Authentication flow:
    1. User logs in manually on the platform
    2. Extract cyberedu_session cookie from browser
    3. Use that cookie for all API requests
    
    Example:
        ```python
        client = CyberEduClient(tenant="cyberedu", session_cookie="cookie_value")
        challenges = client.list_challenges()
        ```
    
    For MCP integration:
        The client can be used directly in MCP tool handlers. All methods
        return JSON-serializable dictionaries suitable for MCP responses.
    """
    
    BASE_URL = "https://api.cyber-edu.co"
    SSO_BASE_URL = "https://sso.cyber-edu.co"
    
    def __init__(
        self,
        tenant: str,
        session_cookie: Optional[str] = None,
        base_url: Optional[str] = None,
        sso_base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize CyberEdu client.
        
        Args:
            tenant: Tenant identifier (e.g., 'cyberedu')
            session_cookie: Optional session cookie value (cyberedu_session)
                           If not provided, must be set via set_session_cookie()
            base_url: Optional API base URL (defaults to https://api.cyber-edu.co)
            sso_base_url: Optional SSO base URL (defaults to https://sso.cyber-edu.co)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.tenant = tenant
        self.session_cookie = session_cookie
        self.BASE_URL = base_url or self.BASE_URL
        self.SSO_BASE_URL = sso_base_url or self.SSO_BASE_URL
        self.timeout = timeout
        
        # Create HTTP client with default headers
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://app.cyber-edu.co',
                'Referer': 'https://app.cyber-edu.co/',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            },
            timeout=self.timeout,
            follow_redirects=True,
        )
    
    # ============================================================================
    # Helper Methods
    # ============================================================================
    
    def set_session_cookie(self, cookie_value: str):
        """Set the session cookie for authentication."""
        self.session_cookie = cookie_value
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get request headers including session cookie.
        
        Args:
            additional_headers: Optional additional headers to include
            
        Returns:
            Dictionary of headers
        """
        headers = {}
        if additional_headers:
            headers.update(additional_headers)
        
        # Add session cookie if available
        if self.session_cookie:
            headers['Cookie'] = f'cyberedu_session={self.session_cookie}'
        
        return headers
    
    def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """
        Make an API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., '/v1/challenge')
            params: Query parameters (will include tenant)
            json_data: JSON body data
            data: Form data
            headers: Additional headers
            
        Returns:
            HTTP response object
        """
        # Add tenant to query parameters
        query_params = params or {}
        query_params['tenant'] = self.tenant
        
        # Prepare headers
        request_headers = self._get_headers(headers)
        
        # Make request
        response = self.client.request(
            method=method,
            url=path,
            params=query_params,
            json=json_data,
            data=data,
            headers=request_headers,
        )
        
        return response
    
    def _extract_download_uuid(self, download_data: Dict[str, Any]) -> str:
        """
        Extract UUID from download response.
        
        Args:
            download_data: JSON response from download endpoint
            
        Returns:
            UUID string
            
        Raises:
            ValueError: If UUID cannot be extracted
        """
        uuid = None
        if 'data' in download_data:
            if isinstance(download_data['data'], dict) and 'uuid' in download_data['data']:
                uuid = download_data['data']['uuid']
            elif isinstance(download_data['data'], str):
                uuid = download_data['data']
        elif 'uuid' in download_data:
            uuid = download_data['uuid']
        
        if not uuid:
            raise ValueError(f"Could not extract download UUID from response: {download_data}")
        
        return uuid
    
    def _handle_flag_submission_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle flag submission response, including 400 status codes.
        
        Args:
            response: HTTP response from flag submission
            
        Returns:
            Submission result dictionary
        """
        # Try to parse JSON response even for 400 status codes
        # The API returns status information in the body even for failed submissions
        try:
            result = response.json()
            # If we got a valid JSON response, return it (even if status code is 400)
            # Only raise for other error status codes
            if response.status_code == 400:
                return result
            response.raise_for_status()
            return result
        except Exception:
            # If JSON parsing fails, raise the HTTP error
            response.raise_for_status()
            return response.json()
    
    def _save_downloaded_file(
        self,
        content: bytes,
        save_path: Union[str, Path],
        response: httpx.Response,
    ) -> Dict[str, Any]:
        """
        Save downloaded file content to disk.
        
        Args:
            content: File content as bytes
            save_path: Path to save the file (directory or full path)
            response: HTTP response object (for extracting filename from headers)
            
        Returns:
            Dictionary with 'path', 'size', and 'success' keys
        """
        save_path = Path(save_path)
        
        # If save_path is a directory, try to get filename from response headers
        if save_path.is_dir() or (not save_path.exists() and not save_path.suffix):
            # Try to extract filename from Content-Disposition header
            filename = None
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                # Parse filename from header: attachment; filename="example.txt"
                import re
                match = re.search(r'filename[*]?=["\']?([^"\';\s]+)["\']?', content_disposition)
                if match:
                    filename = match.group(1)
            
            # Fallback to a default filename if not found
            if not filename:
                filename = 'downloaded_file'
            
            # Ensure directory exists
            save_path.mkdir(parents=True, exist_ok=True)
            save_path = save_path / filename
        else:
            # Ensure parent directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        with open(save_path, 'wb') as f:
            f.write(content)
        
        return {
            'success': True,
            'path': str(save_path.absolute()),
            'size': len(content),
        }
    
    # ============================================================================
    # Authentication & User Methods
    # ============================================================================
    
    def check_auth(self) -> Dict[str, Any]:
        """
        Check if we are authenticated by calling the user endpoint.
        
        Returns:
            User information if authenticated, raises exception otherwise
        """
        # Auth endpoint is on SSO, not API, and doesn't need tenant parameter
        # Build headers with defaults + session cookie
        headers = {
            'Accept': '*/*',
            'Origin': 'https://app.cyber-edu.co',
            'Referer': 'https://app.cyber-edu.co/',
        }
        
        # Add session cookie if available
        if self.session_cookie:
            headers['Cookie'] = f'cyberedu_session={self.session_cookie}'
        
        # Make request to SSO endpoint (not API endpoint)
        response = httpx.get(
            f'{self.SSO_BASE_URL}/auth/user',
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        
        # Response structure: {"data": {...}}
        # Return the data part for easier access
        if 'data' in data:
            return data['data']
        return data
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get full user information including tenants."""
        return self.check_auth()
    
    def list_tenants(self) -> List[Dict[str, Any]]:
        """List all available tenants for the authenticated user."""
        user_info = self.get_user_info()
        return user_info.get('tenants', [])
    
    def get_current_tenant_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently selected tenant."""
        tenants = self.list_tenants()
        for tenant in tenants:
            if tenant.get('selected', False):
                return tenant
        return None
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user information by user ID."""
        response = self._make_request('GET', f'/v1/user/{user_id}')
        response.raise_for_status()
        return response.json()
    
    # ============================================================================
    # Archive Challenge Methods
    # ============================================================================
    
    def list_challenges(
        self,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
        tag_filter: Optional[Union[str, List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all challenges for the current tenant.
        
        The tenant is set via the client (use cyberedu_switch_tenant first for a
        specific org). Returns tenant-filtered challenges with tenant-specific
        solve counts (counts.owned).
        
        Args:
            difficulty: Filter by difficulty (optional)
            category: Filter by category (optional)
            tag_filter: Optional tag filter for client-side filtering. Can be a single
                       tag string or a list of tag strings. Challenges must have at
                       least one matching tag. This is a best-effort filter and may not
                       catch all tenant-specific challenges if tags are inconsistent.
            
        Returns:
            List of challenge dicts with id, title, category, difficulty, points,
            counts.owned (solves), counts.attempts, tags, tenant, etc.
        """
        params = {}
        if difficulty:
            params['difficulty'] = difficulty
        if category:
            params['category'] = category
        
        # Use base endpoint - all information is available here
        response = self._make_request('GET', '/v1/challenge', params=params)
        response.raise_for_status()
        challenges = response.json()
        
        # Apply client-side tag filtering if requested
        if tag_filter:
            if isinstance(tag_filter, str):
                tag_filter = [tag_filter]
            
            # Normalize tag filter to lowercase for case-insensitive matching
            tag_filter_lower = [tag.lower() for tag in tag_filter]
            
            filtered_challenges = []
            for challenge in challenges:
                # Get tags from challenge (could be in 'tags' field or other locations)
                challenge_tags = challenge.get('tags', [])
                if isinstance(challenge_tags, str):
                    challenge_tags = [challenge_tags]
                
                # Check if any tag matches (case-insensitive)
                challenge_tag_lower = [tag.lower() if isinstance(tag, str) else str(tag).lower() 
                                     for tag in challenge_tags]
                
                if any(tag in challenge_tag_lower for tag in tag_filter_lower):
                    filtered_challenges.append(challenge)
            
            return filtered_challenges
        
        return challenges
    
    def list_top_challenges(
        self,
        limit: int = 10,
        sort_by: str = "solves",
    ) -> List[Dict[str, Any]]:
        """
        Get the top N most solved challenges for the current tenant.
        
        Use this when you need leaderboard-style data: "most popular challenges",
        "top solved", "most attempts". Respects the current tenant from
        cyberedu_switch_tenant. Call cyberedu_switch_tenant first if you need
        a specific organization (e.g., unbreakable, cyberedu).
        
        Args:
            limit: Maximum number of challenges to return (default: 10)
            sort_by: Sort criterion - "solves" (counts.owned, most solved first),
                     "attempts" (counts.attempts, most attempted first), or
                     "points" (challenge points, highest first). Default: solves
            
        Returns:
            List of challenge dicts sorted by the chosen criterion, each with
            id, title, difficulty, points, counts.owned (solves), counts.attempts
        """
        challenges = self.list_challenges()
        
        if sort_by == "solves":
            key = lambda c: c.get("counts", {}).get("owned", 0)
        elif sort_by == "attempts":
            key = lambda c: c.get("counts", {}).get("attempts", 0)
        elif sort_by == "points":
            key = lambda c: c.get("points", 0)
        else:
            key = lambda c: c.get("counts", {}).get("owned", 0)
        
        sorted_challenges = sorted(challenges, key=key, reverse=True)
        return sorted_challenges[:limit]
    
    def get_challenge(self, challenge_id: str) -> Dict[str, Any]:
        """Get challenge details."""
        response = self._make_request('GET', f'/v1/challenge/{challenge_id}')
        response.raise_for_status()
        return response.json()
    
    def get_challenge_difficulties(self) -> List[Dict[str, Any]]:
        """Get list of available challenge difficulties."""
        response = self._make_request('GET', '/v1/challenge/difficulties')
        response.raise_for_status()
        return response.json()
    
    def get_challenge_tags(self) -> List[Dict[str, Any]]:
        """Get list of available challenge tags/categories."""
        response = self._make_request('GET', '/v1/challenge/tags')
        response.raise_for_status()
        return response.json()
    
    def subscribe_to_challenge(self, challenge_id: str) -> Dict[str, Any]:
        """Subscribe to (unlock) a challenge."""
        # Build headers similar to other API requests
        headers = self._get_headers({
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://app.cyber-edu.co',
            'Referer': 'https://app.cyber-edu.co/',
        })
        
        # Use GET request (not POST) - the API endpoint uses GET for subscribe
        # The client has base_url configured, so we can use relative path
        response = self.client.get(
            f'/v1/challenge/{challenge_id}/actions/subscribe',
            params={'tenant': self.tenant},
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    
    # ============================================================================
    # Archive Challenge Operations (Flags, Files, Services)
    # ============================================================================
    
    def get_flag(self, challenge_id: str, flag_id: str) -> Dict[str, Any]:
        """Get flag information (question details)."""
        response = self._make_request(
            'GET',
            f'/v1/domain/app/challenge/{challenge_id}/flag/{flag_id}'
        )
        response.raise_for_status()
        return response.json()
    
    def submit_flag(
        self,
        challenge_id: str,
        flag_id: str,
        flag_value: str,
    ) -> Dict[str, Any]:
        """
        Submit a flag/answer for a challenge.
        
        Args:
            challenge_id: Challenge ID
            flag_id: Flag/Question ID
            flag_value: The flag/answer value to submit
            
        Returns:
            Submission result dictionary with 'status' and 'solved' fields.
            Status can be 'success' or 'failed'.
            
        Note:
            The API may return 400 Bad Request for failed submissions, but this
            is expected behavior. The response body will contain the status information.
        """
        # Submit uses multipart/form-data
        # Based on HAR analysis: form fields are 'id' and 'value'
        data = {
            'id': str(flag_id),
            'value': flag_value,
        }
        
        # Use httpx directly for multipart form data
        response = self.client.post(
            f'{self.BASE_URL}/v1/domain/app/challenge/{challenge_id}/submit-attempt',
            params={'tenant': self.tenant},
            data=data,
            headers=self._get_headers(),
        )
        
        return self._handle_flag_submission_response(response)
    
    def download_file(
        self,
        challenge_id: str,
        file_id: str,
        save_path: Optional[Union[str, Path]] = None,
    ) -> Union[bytes, Dict[str, Any]]:
        """
        Download a challenge file.
        
        The download process is two-step:
        1. Request download URL which returns a UUID
        2. Use that UUID to download the actual file from /v1/download/{uuid}
        
        Args:
            challenge_id: Challenge ID
            file_id: File ID
            save_path: Optional path to save the file. Can be a directory or full file path.
                      If a directory, the file will be saved with its original name.
                      If not provided, returns the file content as bytes.
            
        Returns:
            If save_path is provided: Dictionary with 'path', 'size', and 'success' keys
            If save_path is not provided: File content as bytes
        """
        # Step 1: Request download URL - this returns a response with data.data.uuid
        response = self._make_request(
            'GET',
            f'/v1/challenge/{challenge_id}/actions/download/{file_id}'
        )
        response.raise_for_status()
        download_data = response.json()
        
        # Extract UUID from response (structure: data.data.uuid or data.uuid)
        uuid = self._extract_download_uuid(download_data)
        
        # Step 2: Download the actual file using the UUID
        download_response = self._make_request('GET', f'/v1/download/{uuid}')
        download_response.raise_for_status()
        content = download_response.content
        
        # If save_path is provided, save the file to disk
        if save_path is not None:
            return self._save_downloaded_file(content, save_path, download_response)
        
        return content
    
    def start_service(self, challenge_id: str) -> Dict[str, Any]:
        """Start a challenge service (deployment)."""
        response = self._make_request(
            'POST',
            '/v2/governor/archive/domain/app/deployment',
            json_data={'id': challenge_id},
        )
        response.raise_for_status()
        return response.json()
    
    def get_service_status(self, challenge_id: str) -> Dict[str, Any]:
        """Get service/deployment status."""
        # Status endpoint uses POST with JSON body (based on HAR analysis)
        response = self._make_request(
            'POST',
            '/v2/governor/archive/domain/app/deployment/status',
            json_data={'id': challenge_id},
        )
        response.raise_for_status()
        return response.json()
    
    def extend_service(self, challenge_id: str) -> Dict[str, Any]:
        """Extend service/deployment time."""
        response = self._make_request(
            'POST',
            '/v2/governor/archive/domain/app/deployment/extend',
            json_data={'id': challenge_id},
        )
        response.raise_for_status()
        return response.json()
    
    def restart_service(self, challenge_id: str) -> Dict[str, Any]:
        """Restart service/deployment."""
        response = self._make_request(
            'POST',
            '/v2/governor/archive/domain/app/deployment/restart',
            json_data={'id': challenge_id},
        )
        response.raise_for_status()
        return response.json()
    
    # ============================================================================
    # Contest/Event Methods
    # ============================================================================
    
    def list_contests(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all available contests.
        
        Returns:
            Dictionary with 'listedContests' and 'myContests' keys
        """
        response = self._make_request('GET', '/v1/contest')
        response.raise_for_status()
        return response.json()
    
    # ============================================================================
    # Training Methods
    # ============================================================================
    
    def list_trainings(self) -> List[Dict[str, Any]]:
        """
        List all trainings for the current tenant.
        
        Trainings are structured courses (e.g., HeapVault) - different from
        challenges. Availability and count vary by tenant: cyberedu has fewer
        (often paid), unbreakable may have more. Use cyberedu_switch_tenant
        first for a specific org.
        
        Returns:
            List of training dicts with id, slug, title, overview, is_free,
            is_owned, difficulty, modules_count, prices, status, etc.
        """
        response = self._make_request('GET', '/v1/trainings')
        response.raise_for_status()
        data = response.json()
        return data.get('data', []) if isinstance(data, dict) else data

    def get_training(self, training_id_or_slug: str) -> Dict[str, Any]:
        """
        Get full training details including modules with text, images, and deployment info.
        
        Trainings have multiple modules; each module may have content_html (text),
        media (images), files, and a deployment (lab instance). Use this after
        list_trainings to understand structure and content before subscribing.
        
        Args:
            training_id_or_slug: Training UUID or slug (e.g., 'heapvault-training')
            
        Returns:
            Training dict with id, slug, title, overview, modules (list of module
            dicts with content_html, media, files, deployment, challenge), etc.
        """
        response = self._make_request('GET', f'/v1/trainings/{training_id_or_slug}')
        response.raise_for_status()
        data = response.json()
        return data.get('data', data) if isinstance(data, dict) else data

    def subscribe_to_training(self, training_id_or_slug: str) -> Dict[str, Any]:
        """
        Subscribe to (unlock) a training.
        
        Call this to gain access to the training content and deployments.
        Required before accessing module content or starting deployments.
        
        Args:
            training_id_or_slug: Training UUID or slug
            
        Returns:
            Subscription result dictionary
        """
        headers = self._get_headers({
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://app.cyber-edu.co',
            'Referer': 'https://app.cyber-edu.co/',
        })
        response = self.client.get(
            f'/v1/trainings/{training_id_or_slug}/actions/subscribe',
            params={'tenant': self.tenant},
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def download_training_file(
        self,
        training_id: str,
        file_id: str,
        save_path: Optional[Union[str, Path]] = None,
    ) -> Union[bytes, Dict[str, Any]]:
        """
        Download a file from a training (e.g., module attachment or resource).
        
        The download process is two-step:
        1. Request download URL which returns a UUID
        2. Use that UUID to download the actual file from /v1/download/{uuid}
        
        Args:
            training_id: Training UUID
            file_id: File ID (from module's files or media)
            save_path: Optional path to save the file. Can be a directory or full path.
                      If a directory, the file will be saved with its original name.
                      If not provided, returns the file content as bytes.
            
        Returns:
            If save_path is provided: Dictionary with 'path', 'size', and 'success' keys
            If save_path is not provided: File content as bytes
        """
        response = self._make_request(
            'GET',
            f'/v1/trainings/{training_id}/actions/download/{file_id}',
        )
        response.raise_for_status()
        download_data = response.json()
        uuid = self._extract_download_uuid(download_data)
        download_response = self._make_request('GET', f'/v1/download/{uuid}')
        download_response.raise_for_status()
        content = download_response.content
        if save_path is not None:
            return self._save_downloaded_file(content, save_path, download_response)
        return content

    def start_training_service(self, training_id: str) -> Dict[str, Any]:
        """
        Start a training deployment (lab instance).
        
        Trainings with deployments provide a lab environment. Call this to start
        the instance; use get_training_service_status to check when ready.
        
        Args:
            training_id: Training UUID (from get_training or list_trainings)
            
        Returns:
            Deployment result dictionary
        """
        response = self._make_request(
            'POST',
            '/v2/governor/training/domain/app/deployment',
            json_data={'id': training_id},
        )
        response.raise_for_status()
        return response.json()

    def get_training_service_status(self, training_id: str) -> Dict[str, Any]:
        """Get training deployment/service status."""
        response = self._make_request(
            'POST',
            '/v2/governor/training/domain/app/deployment/status',
            json_data={'id': training_id},
        )
        response.raise_for_status()
        return response.json()

    def extend_training_service(self, training_id: str) -> Dict[str, Any]:
        """Extend training deployment time before it expires."""
        response = self._make_request(
            'POST',
            '/v2/governor/training/domain/app/deployment/extend',
            json_data={'id': training_id},
        )
        response.raise_for_status()
        return response.json()

    def restart_training_service(self, training_id: str) -> Dict[str, Any]:
        """Restart a training deployment."""
        response = self._make_request(
            'POST',
            '/v2/governor/training/domain/app/deployment/restart',
            json_data={'id': training_id},
        )
        response.raise_for_status()
        return response.json()

    # ============================================================================
    # Contest Methods
    # ============================================================================

    def get_contest(self, contest_slug: str) -> Dict[str, Any]:
        """
        Get contest details.
        
        Args:
            contest_slug: Contest subdomain/slug (e.g., 'unr24-echipe-final')
            
        Returns:
            Contest details dictionary
        """
        response = self._make_request('GET', f'/v1/contest/{contest_slug}')
        response.raise_for_status()
        return response.json()
    
    def get_contest_ranks(self, contest_slug: str) -> List[Dict[str, Any]]:
        """
        Get contest leaderboard/ranks.
        
        Args:
            contest_slug: Contest subdomain/slug
            
        Returns:
            List of rank entries (teams/users with statistics)
        """
        response = self._make_request('GET', f'/v1/contest/{contest_slug}/ranks')
        response.raise_for_status()
        data = response.json()
        # Response has 'data' key containing the ranks array
        return data.get('data', []) if isinstance(data, dict) else data
    
    def get_contest_challenge(self, contest_slug: str, challenge_id: str) -> Dict[str, Any]:
        """
        Get challenge details within a contest.
        
        Args:
            contest_slug: Contest subdomain/slug
            challenge_id: Challenge ID
            
        Returns:
            Challenge details dictionary
        """
        # Contest challenges require governorType=event and domainIdentifier params
        params = {
            'governorType': 'event',
            'domainIdentifier': contest_slug,
        }
        response = self._make_request(
            'GET',
            f'/v1/contest/{contest_slug}/challenge/{challenge_id}',
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def subscribe_to_contest_challenge(self, contest_slug: str, challenge_id: str) -> Dict[str, Any]:
        """Subscribe to (unlock) a challenge within a contest."""
        headers = self._get_headers({
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://app.cyber-edu.co',
            'Referer': 'https://app.cyber-edu.co/',
        })
        
        response = self.client.get(
            f'/v1/contest/{contest_slug}/challenge/{challenge_id}/actions/subscribe',
            params={'tenant': self.tenant},
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    
    # ============================================================================
    # Contest Challenge Operations (Flags, Files, Services)
    # ============================================================================
    
    def get_contest_flag(self, contest_slug: str, challenge_id: str, flag_id: str) -> Dict[str, Any]:
        """Get flag/question information within a contest."""
        response = self._make_request(
            'GET',
            f'/v1/contest/{contest_slug}/challenge/{challenge_id}/flag/{flag_id}'
        )
        response.raise_for_status()
        return response.json()
    
    def submit_contest_flag(
        self,
        contest_slug: str,
        challenge_id: str,
        flag_id: str,
        flag_value: str,
    ) -> Dict[str, Any]:
        """
        Submit a flag/answer for a challenge within a contest.
        
        Args:
            contest_slug: Contest subdomain/slug
            challenge_id: Challenge ID
            flag_id: Flag/Question ID
            flag_value: The flag/answer value to submit
            
        Returns:
            Submission result dictionary with 'status' and 'solved' fields.
            
        Note:
            The API may return 400 Bad Request for failed submissions, but this
            is expected behavior. The response body will contain the status information.
        """
        data = {
            'id': str(flag_id),
            'value': flag_value,
        }
        
        # Contest flag submission uses /v1/domain/{contest_slug}/challenge/{challenge_id}/submit-attempt
        # Use httpx directly for multipart form data
        response = self.client.post(
            f'{self.BASE_URL}/v1/domain/{contest_slug}/challenge/{challenge_id}/submit-attempt',
            params={'tenant': self.tenant},
            data=data,
            headers=self._get_headers(),
        )
        
        return self._handle_flag_submission_response(response)
    
    def download_contest_file(
        self,
        contest_slug: str,
        challenge_id: str,
        file_id: str,
        save_path: Optional[Union[str, Path]] = None,
    ) -> Union[bytes, Dict[str, Any]]:
        """
        Download a challenge file within a contest.
        
        The download process is two-step:
        1. Request download URL which returns a UUID
        2. Use that UUID to download the actual file from /v1/download/{uuid}
        
        Args:
            contest_slug: Contest subdomain/slug
            challenge_id: Challenge ID
            file_id: File ID
            save_path: Optional path to save the file. Can be a directory or full file path.
                      If a directory, the file will be saved with its original name.
                      If not provided, returns the file content as bytes.
            
        Returns:
            If save_path is provided: Dictionary with 'path', 'size', and 'success' keys
            If save_path is not provided: File content as bytes
        """
        # Step 1: Request download URL
        # Contest downloads use /v1/contest/{slug}/challenge/{id}/download/{file_id}
        # with governorType=event and domainIdentifier query params
        params = {
            'governorType': 'event',
            'domainIdentifier': contest_slug,
        }
        response = self._make_request(
            'GET',
            f'/v1/contest/{contest_slug}/challenge/{challenge_id}/download/{file_id}',
            params=params
        )
        response.raise_for_status()
        download_data = response.json()
        
        # Extract UUID from response
        uuid = self._extract_download_uuid(download_data)
        
        # Step 2: Download the actual file using the UUID
        download_response = self._make_request('GET', f'/v1/download/{uuid}')
        download_response.raise_for_status()
        content = download_response.content
        
        # If save_path is provided, save the file to disk
        if save_path is not None:
            return self._save_downloaded_file(content, save_path, download_response)
        
        return content
    
    def get_contest_service_status(self, contest_slug: str, challenge_id: str) -> Dict[str, Any]:
        """Get service status for a challenge within a contest."""
        # Contest services use POST with JSON body
        # /v2/governor/event/domain/{slug}/deployment/status
        response = self.client.post(
            f'{self.BASE_URL}/v2/governor/event/domain/{contest_slug}/deployment/status',
            params={'tenant': self.tenant},
            json={'id': challenge_id},
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    
    def start_contest_service(self, contest_slug: str, challenge_id: str) -> Dict[str, Any]:
        """Start a challenge service within a contest."""
        response = self.client.post(
            f'{self.BASE_URL}/v2/governor/event/domain/{contest_slug}/deployment',
            params={'tenant': self.tenant},
            json={'id': challenge_id},
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    
    def extend_contest_service(self, contest_slug: str, challenge_id: str) -> Dict[str, Any]:
        """Extend service time for a challenge within a contest."""
        response = self.client.post(
            f'{self.BASE_URL}/v2/governor/event/domain/{contest_slug}/deployment/extend',
            params={'tenant': self.tenant},
            json={'id': challenge_id},
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    
    def restart_contest_service(self, contest_slug: str, challenge_id: str) -> Dict[str, Any]:
        """Restart a challenge service within a contest."""
        response = self.client.post(
            f'{self.BASE_URL}/v2/governor/event/domain/{contest_slug}/deployment/restart',
            params={'tenant': self.tenant},
            json={'id': challenge_id},
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    
    # ============================================================================
    # Context Manager
    # ============================================================================
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
