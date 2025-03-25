from typing import List, Dict, Any, Optional

from app.api.base_client import BaseAPIClient


class UsersAPIClient(BaseAPIClient):
    """
    Client for user-related API operations
    """

    async def get_users(self, company_id: Optional[str] = None, site_id: Optional[str] = None,
                        skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get list of users with optional filtering

        Args:
            company_id: Optional company ID to filter users
            site_id: Optional site ID to filter users
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (pagination)

        Returns:
            List of user dictionaries
        """
        params = {"skip": skip, "limit": limit}
        if company_id:
            params["company_id"] = company_id
        if site_id:
            params["site_id"] = site_id

        return await self.get("/users", params=params)

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get a specific user by ID

        Args:
            user_id: User ID

        Returns:
            User details
        """
        return await self.get(f"/users/{user_id}")

    async def get_current_user(self) -> Dict[str, Any]:
        """
        Get the current authenticated user

        Returns:
            Current user details
        """
        return await self.get("/users/me")

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user

        Args:
            user_data: User data

        Returns:
            Created user details
        """
        return await self.post("/users", json_data=user_data)

    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing user

        Args:
            user_id: User ID
            user_data: Updated user data

        Returns:
            Updated user details
        """
        return await self.put(f"/users/{user_id}", json_data=user_data)

    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        """
        Delete a user

        Args:
            user_id: User ID

        Returns:
            Deleted user details
        """
        return await self.delete(f"/users/{user_id}")


def get_users_client(request):
    """
    Get an instance of the users API client
    """
    return UsersAPIClient(request)