from typing import List, Dict, Any, Optional

from app.api.base_client import BaseAPIClient


class CompaniesAPIClient(BaseAPIClient):
    """
    Client for company-related API operations
    """

    async def get_companies(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of all companies

        Args:
            active_only: If true, only return active companies

        Returns:
            List of company dictionaries
        """
        params = {}
        if active_only:
            params["active_only"] = "true"

        return await self.get("/companies/", params=params)

    async def get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Get a specific company by ID

        Args:
            company_id: Company ID

        Returns:
            Company details
        """
        return await self.get(f"/companies/{company_id}")

    async def create_company(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new company

        Args:
            company_data: Company data

        Returns:
            Created company details
        """
        return await self.post("/companies", json_data=company_data)

    async def update_company(self, company_id: str, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing company

        Args:
            company_id: Company ID
            company_data: Updated company data

        Returns:
            Updated company details
        """
        return await self.put(f"/companies/{company_id}", json_data=company_data)

    async def delete_company(self, company_id: str) -> Dict[str, Any]:
        """
        Delete a company

        Args:
            company_id: Company ID

        Returns:
            Deleted company details
        """
        return await self.delete(f"/companies/{company_id}")

    async def drop_schema(self, company_id: str) -> Dict[str, Any]:
        """
        Drop the database schema for a company

        Args:
            company_id: Company ID

        Returns:
            Response message
        """
        return await self.post(f"/companies/{company_id}/drop-schema", params={"confirm": "true"})


def get_companies_client(request):
    """
    Get an instance of the companies API client
    """
    return CompaniesAPIClient(request)