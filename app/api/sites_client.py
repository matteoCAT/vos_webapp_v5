from typing import List, Dict, Any, Optional

from app.api.base_client import BaseAPIClient


class SitesAPIClient(BaseAPIClient):
    """
    Client for site-related API operations
    """

    async def get_sites(self, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of all restaurant sites/locations

        Args:
            company_id: Optional company ID to filter sites

        Returns:
            List of site dictionaries
        """
        try:
            params = {}
            if company_id:
                params["company_id"] = company_id

            return await self.get("/sites/", params=params)
        except Exception as e:
            print(f"Error fetching sites: {str(e)}")
            # Return empty list on error rather than propagating exception
            return []

    async def get_site(self, site_id: str) -> Dict[str, Any]:
        """
        Get a specific site by ID

        Args:
            site_id: Site ID

        Returns:
            Site details
        """
        return await self.get(f"/sites/{site_id}")

    async def create_site(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new site

        Args:
            site_data: Site data

        Returns:
            Created site details
        """
        return await self.post("/sites", json_data=site_data)

    async def update_site(self, site_id: str, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing site

        Args:
            site_id: Site ID
            site_data: Updated site data

        Returns:
            Updated site details
        """
        return await self.put(f"/sites/{site_id}", json_data=site_data)

    async def delete_site(self, site_id: str) -> Dict[str, Any]:
        """
        Delete a site

        Args:
            site_id: Site ID

        Returns:
            Deleted site details
        """
        return await self.delete(f"/sites/{site_id}")


def get_sites_client(request):
    """
    Get an instance of the sites API client
    """
    return SitesAPIClient(request)