from typing import Any, Dict, List, Optional, Union
import json

import httpx
from starlette.requests import Request

from app.config import settings


class BaseAPIClient:
    """
    Base client for interacting with the backend API
    """

    def __init__(self, request: Request):
        """
        Initialize the API client with the current request

        Args:
            request: The current request object
        """
        self.request = request
        self.http_client = request.app.state.http_client
        self.access_token = request.session.get(settings.AUTH_TOKEN_NAME)
        self.refresh_token = request.session.get(settings.AUTH_REFRESH_TOKEN_NAME)

    async def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests

        Returns:
            Dict with authorization headers if token is available
        """
        headers = {"Accept": "application/json"}

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        return headers

    async def _handle_response(self, response: httpx.Response, retry_on_auth_error: bool = True) -> Any:
        """
        Handle API response and return JSON data

        Args:
            response: Response from the API
            retry_on_auth_error: Whether to retry with token refresh on auth errors

        Returns:
            Parsed JSON data from the response

        Raises:
            httpx.HTTPStatusError: If the response has an error status code
        """
        try:
            # Raise exception for error status codes
            response.raise_for_status()

            # Return JSON data if content exists
            if response.content:
                return response.json()
            return None
        except httpx.HTTPStatusError as e:
            # Handle authentication errors - try to refresh token if needed
            if retry_on_auth_error and e.response.status_code == 401 and self.refresh_token:
                print("Token expired, attempting to refresh...")

                try:
                    # Import here to avoid circular import
                    from app.api.auth_client import get_auth_client
                    auth_client = get_auth_client(self.request)

                    # Refresh token
                    tokens = await auth_client.refresh_token()

                    # Update tokens in session
                    if "session" in self.request.scope:
                        from app.config import settings
                        self.request.session[settings.AUTH_TOKEN_NAME] = tokens["access_token"]
                        self.request.session[settings.AUTH_REFRESH_TOKEN_NAME] = tokens["refresh_token"]

                        # Update tokens in client
                        self.access_token = tokens["access_token"]
                        self.refresh_token = tokens["refresh_token"]

                        # Retry the original request with new token
                        headers = await self._get_headers()
                        retried_response = await self.http_client.request(
                            response.request.method,
                            response.request.url,
                            headers=headers,
                            content=response.request.content,
                        )

                        # Handle the retried response (without recursive retry)
                        return await self._handle_response(retried_response, retry_on_auth_error=False)

                except Exception as refresh_error:
                    print(f"Error refreshing token: {refresh_error}")

                    # If token refresh fails, raise the original error
                    raise e

            # If not an auth error or refresh failed, re-raise the original error
            raise

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Send GET request to the API

        Args:
            path: API endpoint path
            params: Query parameters

        Returns:
            API response data
        """
        headers = await self._get_headers()
        response = await self.http_client.get(path, headers=headers, params=params)
        return await self._handle_response(response)

    async def post(self, path: str, data: Optional[Dict[str, Any]] = None,
                   json_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Send POST request to the API

        Args:
            path: API endpoint path
            data: Form data
            json_data: JSON data

        Returns:
            API response data
        """
        headers = await self._get_headers()
        response = await self.http_client.post(
            path, headers=headers, data=data, json=json_data
        )
        return await self._handle_response(response)

    async def put(self, path: str, data: Optional[Dict[str, Any]] = None,
                  json_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Send PUT request to the API

        Args:
            path: API endpoint path
            data: Form data
            json_data: JSON data

        Returns:
            API response data
        """
        headers = await self._get_headers()
        response = await self.http_client.put(
            path, headers=headers, data=data, json=json_data
        )
        return await self._handle_response(response)

    async def delete(self, path: str) -> Any:
        """
        Send DELETE request to the API

        Args:
            path: API endpoint path

        Returns:
            API response data
        """
        headers = await self._get_headers()
        response = await self.http_client.delete(path, headers=headers)
        return await self._handle_response(response)