from typing import Any, Dict, List, Optional, Union
import json

import httpx
from starlette.requests import Request

from app.config import settings


class APIClient:
    """
    Client for interacting with the backend API
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

    async def _handle_response(self, response: httpx.Response) -> Any:
        """
        Handle API response and return JSON data

        Args:
            response: Response from the API

        Returns:
            Parsed JSON data from the response

        Raises:
            httpx.HTTPStatusError: If the response has an error status code
        """
        # Raise exception for error status codes
        response.raise_for_status()

        # Return JSON data if content exists
        if response.content:
            return response.json()
        return None

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

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with email and password

        Args:
            email: User email
            password: User password

        Returns:
            Authentication response with tokens and user data
        """
        # Use the JSON login endpoint from the FastAPI backend
        response = await self.http_client.post(
            "/auth/login/json",
            json={"email": email, "password": password}
        )

        # Handle response and extract data
        auth_data = await self._handle_response(response)

        # Store tokens in client instance
        self.access_token = auth_data["access_token"]
        self.refresh_token = auth_data["refresh_token"]

        # Get user details with the new token
        headers = {"Authorization": f"Bearer {self.access_token}"}
        user_response = await self.http_client.get("/users/me", headers=headers)
        user_data = await self._handle_response(user_response)

        return {
            "tokens": auth_data,
            "user": user_data
        }

    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using the refresh token

        Returns:
            New tokens from the API
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        response = await self.http_client.post(
            "/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )

        auth_data = await self._handle_response(response)

        # Update tokens in client instance
        self.access_token = auth_data["access_token"]
        self.refresh_token = auth_data["refresh_token"]

        return auth_data

    async def get_sites(self) -> List[Dict[str, Any]]:
        """
        Get list of all restaurant sites/locations

        Returns:
            List of site dictionaries
        """
        try:
            print(f"Fetching sites from {self.http_client.base_url}/sites")
            return await self.get("/sites/")
        except Exception as e:
            print(f"Error fetching sites: {str(e)}")
            # Return empty list on error rather than propagating exception
            return []

    async def logout(self) -> None:
        """
        Log out the current user by invalidating the refresh token
        """
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            try:
                await self.http_client.post("/auth/logout", headers=headers)
            except httpx.HTTPStatusError:
                # Ignore errors on logout, we'll clear the session anyway
                pass

        # Clear tokens from client instance
        self.access_token = None
        self.refresh_token = None


def get_api_client(request: Request) -> APIClient:
    """
    Get an API client instance for the current request

    Args:
        request: The current request

    Returns:
        APIClient instance
    """
    return APIClient(request)