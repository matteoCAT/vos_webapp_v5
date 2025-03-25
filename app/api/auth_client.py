from typing import Dict, Any

from app.api.base_client import BaseAPIClient


class AuthAPIClient(BaseAPIClient):
    """
    Client for authentication-related API operations
    """

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

        # We need to use a direct http_client call here to avoid circular refresh attempts
        response = await self.http_client.post(
            "/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )

        # Handle the response manually since we can't use _handle_response (would cause circular refresh)
        if response.status_code >= 400:
            response.raise_for_status()  # This will raise an appropriate HTTPStatusError

        auth_data = response.json()

        # Update tokens in client instance
        self.access_token = auth_data["access_token"]
        self.refresh_token = auth_data["refresh_token"]

        return auth_data

    async def logout(self) -> None:
        """
        Log out the current user by invalidating the refresh token
        """
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            try:
                await self.http_client.post("/auth/logout", headers=headers)
            except Exception:
                # Ignore errors on logout, we'll clear the session anyway
                pass

        # Clear tokens from client instance
        self.access_token = None
        self.refresh_token = None


def get_auth_client(request):
    """
    Get an instance of the auth API client
    """
    return AuthAPIClient(request)