from typing import List, Dict, Any, Optional

from app.api.base_client import BaseAPIClient


class RolesAPIClient(BaseAPIClient):
    """
    Client for role-related API operations
    """

    async def get_roles(self) -> List[Dict[str, Any]]:
        """
        Get list of all roles

        Returns:
            List of role dictionaries
        """
        return await self.get("/roles/")

    async def get_role(self, role_id: str) -> Dict[str, Any]:
        """
        Get a specific role by ID

        Args:
            role_id: Role ID

        Returns:
            Role details
        """
        return await self.get(f"/roles/{role_id}")

    async def create_role(self, role_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new role

        Args:
            role_data: Role data

        Returns:
            Created role details
        """
        return await self.post("/roles", json_data=role_data)

    async def update_role(self, role_id: str, role_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing role

        Args:
            role_id: Role ID
            role_data: Updated role data

        Returns:
            Updated role details
        """
        return await self.put(f"/roles/{role_id}", json_data=role_data)

    async def delete_role(self, role_id: str) -> Dict[str, Any]:
        """
        Delete a role

        Args:
            role_id: Role ID

        Returns:
            Deleted role details
        """
        return await self.delete(f"/roles/{role_id}")

    async def update_role_permissions(self, role_id: str,
                                      add_permission_ids: List[str] = None,
                                      remove_permission_ids: List[str] = None) -> Dict[str, Any]:
        """
        Update role permissions

        Args:
            role_id: Role ID
            add_permission_ids: List of permission IDs to add
            remove_permission_ids: List of permission IDs to remove

        Returns:
            Updated role details
        """
        data = {}
        if add_permission_ids:
            data["add_permission_ids"] = add_permission_ids
        if remove_permission_ids:
            data["remove_permission_ids"] = remove_permission_ids

        return await self.put(f"/roles/{role_id}/permissions", json_data=data)


def get_roles_client(request):
    """
    Get an instance of the roles API client
    """
    return RolesAPIClient(request)