from typing import List, Dict, Any, Optional

from app.api.base_client import BaseAPIClient


class PermissionsAPIClient(BaseAPIClient):
    """
    Client for permission-related API operations
    """

    async def get_permissions(self, module: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of all permissions

        Args:
            module: Optional module name to filter permissions

        Returns:
            List of permission dictionaries
        """
        params = {}
        if module:
            params["module"] = module

        return await self.get("/permissions/", params=params)

    async def get_permission(self, permission_id: str) -> Dict[str, Any]:
        """
        Get a specific permission by ID

        Args:
            permission_id: Permission ID

        Returns:
            Permission details
        """
        return await self.get(f"/permissions/{permission_id}")

    async def get_modules(self) -> List[str]:
        """
        Get list of all permission modules

        Returns:
            List of module names
        """
        return await self.get("/permissions/modules")

    async def create_permission(self, permission_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new permission

        Args:
            permission_data: Permission data

        Returns:
            Created permission details
        """
        return await self.post("/permissions", json_data=permission_data)

    async def update_permission(self, permission_id: str, permission_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing permission

        Args:
            permission_id: Permission ID
            permission_data: Updated permission data

        Returns:
            Updated permission details
        """
        return await self.put(f"/permissions/{permission_id}", json_data=permission_data)

    async def delete_permission(self, permission_id: str) -> Dict[str, Any]:
        """
        Delete a permission

        Args:
            permission_id: Permission ID

        Returns:
            Deleted permission details
        """
        return await self.delete(f"/permissions/{permission_id}")

    async def initialize_permissions(self) -> Dict[str, Any]:
        """
        Initialize permissions from registry

        Returns:
            Response message
        """
        return await self.post("/permissions/initialize")


def get_permissions_client(request):
    """
    Get an instance of the permissions API client
    """
    return PermissionsAPIClient(request)