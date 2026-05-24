import httpx

from app.config import get_settings
from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult

_JURISDICTION_MAP: dict[str, str] = {
    "GB": "gb",
    "US": "us_de",
    "DE": "de",
    "FR": "fr",
    "AU": "au",
    "CA": "ca",
    "NL": "nl",
    "IE": "ie",
    "SG": "sg",
    "HK": "hk",
    "CN": "cn",
    "JP": "jp",
    "IN": "in",
}


class OpenCorporatesModule(BaseSearchModule):
    module_id = "open_corporates"
    module_name = "OpenCorporates"
    description = (
        "Global company registry data from OpenCorporates — covers 130+ jurisdictions "
        "including company status, officers, alternative names, and incorporation details."
    )
    jurisdictions = None  # global

    _BASE_URL = "https://api.opencorporates.com/v0.4"

    output_schema = {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "company_number": {"type": "string"},
            "jurisdiction": {"type": "string"},
            "current_status": {"type": ["string", "null"]},
            "incorporation_date": {"type": ["string", "null"]},
            "dissolution_date": {"type": ["string", "null"]},
            "company_type": {"type": ["string", "null"]},
            "registered_address": {"type": ["string", "null"]},
            "officers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "position": {"type": "string"},
                        "start_date": {"type": ["string", "null"]},
                        "end_date": {"type": ["string", "null"]},
                        "is_current": {"type": "boolean"},
                    },
                },
            },
            "alternative_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Trading names, previous names, and other known aliases",
            },
            "source_url": {"type": "string"},
        },
    }

    system_prompt = (
        "You are a company analyst with expertise in global corporate data. "
        "Extract and structure company information from OpenCorporates API data. "
        "Pay special attention to alternative_names — include ALL previous names, "
        "trading names, and known aliases listed in the source data."
    )

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        settings = get_settings()
        params: dict = {}
        if settings.opencorporates_api_token:
            params["api_token"] = settings.opencorporates_api_token

        jur_code = _JURISDICTION_MAP.get(context.jurisdiction.upper(), context.jurisdiction.lower())

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if context.registration_number:
                    resp = await client.get(
                        f"{self._BASE_URL}/companies/{jur_code}/{context.registration_number}",
                        params=params,
                    )
                    if resp.status_code == 200:
                        company = resp.json().get("results", {}).get("company", {})
                        officers_resp = await client.get(
                            f"{self._BASE_URL}/companies/{jur_code}"
                            f"/{context.registration_number}/officers",
                            params=params,
                        )
                        officers = (
                            officers_resp.json().get("results", {})
                            if officers_resp.status_code == 200
                            else {}
                        )
                        return SearchModuleResult(
                            raw_data={"company": company, "officers": officers}
                        )

                if context.company_name:
                    search_params = {
                        **params,
                        "q": context.company_name,
                        "jurisdiction_code": jur_code,
                    }
                    resp = await client.get(
                        f"{self._BASE_URL}/companies/search", params=search_params
                    )
                    if resp.status_code == 200:
                        companies = resp.json().get("results", {}).get("companies", [])
                        if companies:
                            top = companies[0].get("company", {})
                            return SearchModuleResult(
                                raw_data={
                                    "company": top,
                                    "search_results_count": len(companies),
                                }
                            )
                        return SearchModuleResult(
                            error=f"No company found in OpenCorporates for "
                            f"'{context.company_name}' in {jur_code}"
                        )

                return SearchModuleResult(error="No valid identifiers provided")

        except httpx.HTTPStatusError as exc:
            return SearchModuleResult(
                error=f"OpenCorporates API error {exc.response.status_code}"
            )
        except Exception as exc:
            return SearchModuleResult(error=str(exc))

