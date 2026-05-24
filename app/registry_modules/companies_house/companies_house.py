import logging
from typing import List

import httpx

from app.config import get_settings
from app.models.context import SearchContext
from app.models.response import CandidateCompany
from app.registry_modules.base import BaseRegistryModule

logger = logging.getLogger(__name__)

_MAX_CANDIDATES = 10


class CompaniesHouseRegistryModule(BaseRegistryModule):
    module_id = "companies_house_registry"
    module_name = "Companies House Registry"
    jurisdictions = ["GB"]

    _BASE_URL = "https://api.company-information.service.gov.uk"

    async def search_companies(self, context: SearchContext) -> List[CandidateCompany]:
        settings = get_settings()

        auth = (settings.companies_house_api_key, "")
        try:
            async with httpx.AsyncClient(auth=auth, timeout=15.0) as client:
                if context.registration_number:
                    return await self._fetch_by_number(client, context.registration_number)
                if context.company_name:
                    return await self._search_by_name(client, context.company_name)
            return []
        except Exception as exc:
            logger.error("Companies House registry search failed: %s", exc)
            return []

    async def _fetch_by_number(self, client: httpx.AsyncClient, number: str) -> List[CandidateCompany]:
        resp = await client.get(f"{self._BASE_URL}/company/{number}")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        return [CandidateCompany(
            company_name=data.get("company_name", ""),
            registration_number=data.get("company_number", number),
            jurisdiction="GB",
            company_status=data.get("company_status"),
            source=self.module_name,
        )]

    async def _search_by_name(self, client: httpx.AsyncClient, name: str) -> List[CandidateCompany]:
        resp = await client.get(
            f"{self._BASE_URL}/search/companies",
            params={"q": name, "items_per_page": _MAX_CANDIDATES},
        )
        resp.raise_for_status()
        return [
            CandidateCompany(
                company_name=item.get("title", ""),
                registration_number=item.get("company_number", ""),
                jurisdiction="GB",
                company_status=item.get("company_status"),
                source=self.module_name,
            )
            for item in resp.json().get("items", [])
            if item.get("company_number")
        ]
