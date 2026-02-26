#!/usr/bin/env python3
"""
MCP Client - Model Context Protocol Client for Silver Tier

Provides a base client for communicating with MCP servers for external integrations
(Gmail send, LinkedIn, Facebook, Twitter, WhatsApp).

Implements connection management, authentication, and error handling for all MCP
server communications.

MCP Protocol: https://modelcontextprotocol.io/
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    raise ImportError(
        "requests library is required. Install with: uv pip install requests"
    )


logger = logging.getLogger(__name__)


class MCPErrorType(Enum):
    """MCP error types for categorization."""
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    VALIDATION_ERROR = "validation_error"
    SERVER_ERROR = "server_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class MCPResponse:
    """Standardized MCP response object."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[MCPErrorType] = None
    status_code: Optional[int] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry


class MCPClient:
    """
    Base MCP client for communicating with Model Context Protocol servers.

    Handles:
    - Connection management with connection pooling
    - Error handling and categorization
    - Authentication token management
    - Retry logic with exponential backoff
    - Request/response logging

    Usage:
        client = MCPClient(
            server_url="http://localhost:3001/gmail",
            api_key=os.getenv("GMAIL_API_KEY")
        )
        response = client.post("/send_email", data={"to": "user@example.com", ...})
        if response.success:
            print("Email sent:", response.data)
        else:
            print("Error:", response.error)
    """

    def __init__(
        self,
        server_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        dry_run: bool = False,
        token_refresh_callback: Optional[callable] = None
    ):
        """
        Initialize MCP client.

        Args:
            server_url: Base URL of the MCP server (e.g., "http://localhost:3001/gmail")
            api_key: API key or auth token for the MCP server
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)
            dry_run: If True, log requests but don't actually call MCP server
            token_refresh_callback: Optional function to call when token expires (401 error)
                                  Should return new token string or None
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.dry_run = dry_run or os.getenv("DRY_RUN", "false").lower() == "true"
        self.token_refresh_callback = token_refresh_callback
        self._token_refreshed = False  # Track if we already tried refreshing token

        # Create session with connection pooling
        self.session = requests.Session()

        # Configure retry strategy (will be enhanced in T009)
        retry_strategy = Retry(
            total=0,  # We'll handle retries manually for now
            backoff_factor=0,
            status_forcelist=[],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'AI-Employee-Silver/0.2.0'
        })

        # Add auth header if api_key provided
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })

        logger.info(
            f"MCPClient initialized: {self.server_url} "
            f"(timeout={timeout}s, max_retries={max_retries}, dry_run={self.dry_run})"
        )

    def _refresh_token(self) -> bool:
        """
        Attempt to refresh the authentication token using the provided callback.

        Returns:
            True if token was successfully refreshed, False otherwise
        """
        if not self.token_refresh_callback:
            logger.warning("Token refresh callback not provided - cannot refresh token")
            return False

        if self._token_refreshed:
            logger.warning("Token already refreshed once - not retrying to avoid loop")
            return False

        try:
            logger.info("Attempting to refresh authentication token...")
            new_token = self.token_refresh_callback()

            if new_token:
                self.api_key = new_token
                self.session.headers.update({
                    'Authorization': f'Bearer {new_token}'
                })
                self._token_refreshed = True
                logger.info("Authentication token refreshed successfully")
                return True
            else:
                logger.error("Token refresh callback returned None")
                return False

        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return False

    def _should_retry(self, error_type: MCPErrorType) -> bool:
        """
        Determine if a request should be retried based on error type.

        Args:
            error_type: The type of error that occurred

        Returns:
            True if the error is transient and request should be retried
        """
        # Retry transient errors (connection, timeout, server errors)
        # Do NOT retry authentication, validation, or rate limit errors
        retriable_errors = [
            MCPErrorType.CONNECTION_ERROR,
            MCPErrorType.TIMEOUT_ERROR,
            MCPErrorType.SERVER_ERROR
        ]
        return error_type in retriable_errors

    def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        Make HTTP request with exponential backoff retry logic.

        Retry strategy:
        - Attempt 1: No delay
        - Attempt 2: 1s delay
        - Attempt 3: 2s delay
        - Attempt 4: 4s delay
        - Max retries: 3 (total 4 attempts)
        - Max delay: 60s

        Only retries transient errors (connection, timeout, server errors).
        Does NOT retry authentication, validation, or rate limit errors.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/send_email")
            data: Request body data (for POST/PUT)
            params: Query parameters (for GET)

        Returns:
            MCPResponse with success status and data/error
        """
        attempt = 0
        last_response = None

        while attempt <= self.max_retries:
            # Calculate exponential backoff delay: 1s, 2s, 4s, 8s (max 60s)
            if attempt > 0:
                delay = min(2 ** (attempt - 1), 60)
                logger.info(
                    f"Retrying request (attempt {attempt + 1}/{self.max_retries + 1}) "
                    f"after {delay}s delay..."
                )
                time.sleep(delay)

            # Make the request
            response = self._make_request(method, endpoint, data, params)
            last_response = response

            # Success - return immediately
            if response.success:
                if attempt > 0:
                    logger.info(f"Request succeeded after {attempt} retries")
                return response

            # Check if error is retriable
            if not response.error_type or not self._should_retry(response.error_type):
                logger.warning(
                    f"Non-retriable error ({response.error_type}) - not retrying"
                )
                return response

            # Log the failure and prepare for retry
            logger.warning(
                f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): "
                f"{response.error_type.value} - {response.error}"
            )

            attempt += 1

        # Max retries exceeded
        logger.error(
            f"Request failed after {self.max_retries + 1} attempts: {last_response.error}"
        )
        return last_response

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        Internal method to make HTTP requests to MCP server (single attempt).

        This method makes a single HTTP request without retry logic.
        Use _make_request_with_retry() for automatic retry handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/send_email")
            data: Request body data (for POST/PUT)
            params: Query parameters (for GET)

        Returns:
            MCPResponse with success status and data/error
        """
        url = f"{self.server_url}{endpoint}"

        # DRY_RUN mode - log but don't execute
        if self.dry_run:
            logger.info(
                f"[DRY_RUN] {method} {url} - data={data}, params={params}"
            )
            return MCPResponse(
                success=True,
                data={"message": "DRY_RUN mode - request logged but not executed"},
                status_code=200
            )

        try:
            # Make the actual HTTP request
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )

            # Log request/response
            logger.debug(
                f"{method} {url} - Status: {response.status_code}, "
                f"Response: {response.text[:200]}"
            )

            # Handle response
            if response.status_code == 200 or response.status_code == 201:
                # Reset token refresh flag on success
                self._token_refreshed = False
                return MCPResponse(
                    success=True,
                    data=response.json() if response.content else {},
                    status_code=response.status_code
                )
            elif response.status_code == 401:
                # Authentication error - try to refresh token and retry
                logger.warning(f"Authentication error (401) for {url}")

                if self._refresh_token():
                    # Token refreshed successfully - retry the request
                    logger.info("Retrying request with refreshed token...")
                    return self._make_request(method, endpoint, data, params)
                else:
                    # Token refresh failed or not available
                    return MCPResponse(
                        success=False,
                        error="Authentication failed - invalid or expired token (refresh failed)",
                        error_type=MCPErrorType.AUTHENTICATION_ERROR,
                        status_code=401
                    )
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                return MCPResponse(
                    success=False,
                    error="Rate limit exceeded",
                    error_type=MCPErrorType.RATE_LIMIT_ERROR,
                    status_code=429,
                    retry_after=retry_after
                )
            elif response.status_code >= 500:
                return MCPResponse(
                    success=False,
                    error=f"Server error: {response.text}",
                    error_type=MCPErrorType.SERVER_ERROR,
                    status_code=response.status_code
                )
            else:
                return MCPResponse(
                    success=False,
                    error=f"Request failed: {response.text}",
                    error_type=MCPErrorType.VALIDATION_ERROR,
                    status_code=response.status_code
                )

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout: {url}")
            return MCPResponse(
                success=False,
                error=f"Request timeout after {self.timeout}s",
                error_type=MCPErrorType.TIMEOUT_ERROR
            )

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {url} - {str(e)}")
            return MCPResponse(
                success=False,
                error=f"Connection error: {str(e)}",
                error_type=MCPErrorType.CONNECTION_ERROR
            )

        except Exception as e:
            logger.error(f"Unexpected error: {url} - {str(e)}")
            return MCPResponse(
                success=False,
                error=f"Unexpected error: {str(e)}",
                error_type=MCPErrorType.UNKNOWN_ERROR
            )

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        Make GET request to MCP server with automatic retry logic.

        Args:
            endpoint: API endpoint (e.g., "/messages")
            params: Query parameters

        Returns:
            MCPResponse with success status and data/error
        """
        return self._make_request_with_retry("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        Make POST request to MCP server with automatic retry logic.

        Args:
            endpoint: API endpoint (e.g., "/send_email")
            data: Request body data

        Returns:
            MCPResponse with success status and data/error
        """
        return self._make_request_with_retry("POST", endpoint, data=data)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        Make PUT request to MCP server with automatic retry logic.

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            MCPResponse with success status and data/error
        """
        return self._make_request_with_retry("PUT", endpoint, data=data)

    def delete(
        self,
        endpoint: str
    ) -> MCPResponse:
        """
        Make DELETE request to MCP server with automatic retry logic.

        Args:
            endpoint: API endpoint

        Returns:
            MCPResponse with success status and data/error
        """
        return self._make_request_with_retry("DELETE", endpoint)

    def close(self):
        """Close the session and clean up resources."""
        self.session.close()
        logger.info(f"MCPClient closed: {self.server_url}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Example: Gmail MCP client
    with MCPClient(
        server_url="http://localhost:3001/gmail",
        api_key="test-key",
        dry_run=True
    ) as client:
        response = client.post("/send_email", data={
            "to": "user@example.com",
            "subject": "Test",
            "body": "Hello"
        })
        print(f"Success: {response.success}, Data: {response.data}")
