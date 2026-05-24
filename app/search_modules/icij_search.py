import httpx

from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult


class ICIJSearchModule(BaseSearchModule):
    module_id = "icij_leaks"
    module_name = "ICIJ Offshore Leaks"
    description = (
        "Searches the ICIJ Offshore Leaks database — Panama Papers, Paradise Papers, "
        "Pandora Papers, Bahamas Leaks, and Offshore Leaks."
    )
    jurisdictions = None  # global
    module_tier = "search"

    _BASE_URL = "https://offshoreleaks.icij.org/api/v1"

    output_schema = {
        "type": "object",
        "properties": {
            "is_mentioned_in_leaks": {"type": "boolean"},
            "entities_found": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "dataset": {
                            "type": "string",
                            "description": (
                                "e.g. Panama Papers, Paradise Papers, "
                                "Pandora Papers, Bahamas Leaks"
                            ),
                        },
                        "entity_type": {
                            "type": "string",
                            "description": "e.g. Entity, Officer, Intermediary",
                        },
                        "jurisdiction": {"type": ["string", "null"]},
                        "linked_officers": {"type": "array", "items": {"type": "string"}},
                        "source_url": {"type": "string"},
                    },
                },
            },
            "summary": {"type": "string"},
        },
    }

    system_prompt = (
        "You are an investigative analyst specialising in offshore financial structures. "
        "Determine whether the company or its associated principals appear in ICIJ leak databases. "
        "Identify the specific leak dataset, jurisdiction, and any linked entities or officers."
    )

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        if not context.company_name:
            return SearchModuleResult(error="Company name is required for ICIJ search")

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{self._BASE_URL}/entities",
                    params={"q": context.company_name},
                    headers={"Accept": "application/json"},
                )

            if resp.status_code != 200:
                return SearchModuleResult(error=f"ICIJ API returned HTTP {resp.status_code}")

            results = resp.json().get("results", [])
            return SearchModuleResult(
                raw_data={"count": len(results), "results": results}
            )

        except httpx.TimeoutException:
            return SearchModuleResult(error="ICIJ search timed out")
        except Exception as exc:
            return SearchModuleResult(error=f"ICIJ search failed: {exc}")
