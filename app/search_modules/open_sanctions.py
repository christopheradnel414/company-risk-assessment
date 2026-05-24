import httpx

from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult


class OpenSanctionsModule(BaseSearchModule):
    module_id = "open_sanctions"
    module_name = "OpenSanctions"
    description = (
        "Searches global sanctions lists, watchlists, and politically exposed persons (PEP) "
        "databases via OpenSanctions — covers OFAC, UN, EU, and 200+ other sources."
    )
    jurisdictions = None  # global
    module_tier = "search"

    _BASE_URL = "https://api.opensanctions.org"

    output_schema = {
        "type": "object",
        "properties": {
            "is_sanctioned": {"type": "boolean"},
            "sanctions_found": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string"},
                        "schema_type": {
                            "type": "string",
                            "description": "e.g. Company, Organization, Person",
                        },
                        "datasets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sanctions datasets this entity appears in",
                        },
                        "sanctions_programs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "e.g. OFAC SDN, EU Consolidated, UN Consolidated",
                        },
                        "start_date": {"type": ["string", "null"]},
                        "reason": {"type": ["string", "null"]},
                        "jurisdiction": {"type": ["string", "null"]},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "summary": {"type": "string"},
        },
    }

    system_prompt = (
        "You are a compliance analyst specialising in sanctions screening. "
        "Determine whether the company appears on any international sanctions lists or watchlists. "
        "Identify the specific programs, issuing bodies, and the reason for listing if available."
    )

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        if not context.company_name:
            return SearchModuleResult(error="Company name is required for sanctions search")

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{self._BASE_URL}/search/entities",
                    params={"q": context.company_name, "schema": "Company,Organization", "limit": 10},
                    headers={"Accept": "application/json"},
                )

            if resp.status_code == 429:
                return SearchModuleResult(error="OpenSanctions rate limit exceeded")
            if resp.status_code != 200:
                return SearchModuleResult(error=f"OpenSanctions API returned HTTP {resp.status_code}")

            results = resp.json().get("results", [])
            return SearchModuleResult(raw_data={"results": results})

        except httpx.TimeoutException:
            return SearchModuleResult(error="OpenSanctions search timed out")
        except Exception as exc:
            return SearchModuleResult(error=f"OpenSanctions search failed: {exc}")
