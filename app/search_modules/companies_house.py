import asyncio

import httpx

from app.config import get_settings
from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult


class CompaniesHouseModule(BaseSearchModule):
    module_id = "companies_house"
    module_name = "Companies House"
    description = (
        "Official UK Companies House registry — company profile, filing history, "
        "officers, and persons with significant control (PSC)."
    )
    jurisdictions = ["GB"]

    _BASE_URL = "https://api.company-information.service.gov.uk"

    output_schema = {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "company_number": {"type": "string"},
            "company_status": {
                "type": "string",
                "description": "e.g. active, dissolved, liquidation, administration",
            },
            "company_type": {"type": "string"},
            "incorporation_date": {"type": ["string", "null"]},
            "previous_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Former registered names from filing history",
            },
            "registered_address": {
                "type": "object",
                "properties": {
                    "address_line_1": {"type": "string"},
                    "address_line_2": {"type": ["string", "null"]},
                    "locality": {"type": "string"},
                    "postal_code": {"type": "string"},
                    "country": {"type": "string"},
                },
            },
            "sic_codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Standard Industrial Classification codes",
            },
            "officers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                        "appointed_on": {"type": ["string", "null"]},
                        "resigned_on": {"type": ["string", "null"]},
                        "nationality": {"type": ["string", "null"]},
                        "country_of_residence": {"type": ["string", "null"]},
                    },
                },
            },
            "persons_with_significant_control": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "natures_of_control": {"type": "array", "items": {"type": "string"}},
                        "nationality": {"type": ["string", "null"]},
                        "country_of_residence": {"type": ["string", "null"]},
                    },
                },
            },
            "accounts": {
                "type": "object",
                "properties": {
                    "last_accounts_date": {"type": ["string", "null"]},
                    "accounts_overdue": {"type": "boolean"},
                    "next_accounts_due": {"type": ["string", "null"]},
                },
            },
            "confirmation_statement_overdue": {"type": "boolean"},
            "recent_filings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "type": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            },
        },
    }

    system_prompt = (
        "You are a company analyst specialising in UK corporate data. "
        "Extract and structure information from Companies House API responses. "
        "Pay attention to previous company names in the filing history (look for CERTNM filings). "
        "Focus on compliance status, officer details, and any overdue filings."
    )

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        settings = get_settings()
        api_key = settings.companies_house_api_key

        if not api_key:
            return SearchModuleResult(
                error="Companies House API key not configured. Set COMPANIES_HOUSE_API_KEY in .env"
            )

        try:
            async with httpx.AsyncClient(auth=(api_key, ""), timeout=30.0) as client:
                company_number = context.registration_number

                if not company_number:
                    search_resp = await client.get(
                        f"{self._BASE_URL}/search/companies",
                        params={"q": context.company_name, "items_per_page": 1},
                    )
                    search_resp.raise_for_status()
                    items = search_resp.json().get("items", [])
                    if not items:
                        return SearchModuleResult(
                            error=f"No company found in Companies House with name: {context.company_name}"
                        )
                    company_number = items[0]["company_number"]

                profile_resp, officers_resp, filings_resp, psc_resp = await asyncio.gather(
                    client.get(f"{self._BASE_URL}/company/{company_number}"),
                    client.get(f"{self._BASE_URL}/company/{company_number}/officers"),
                    client.get(
                        f"{self._BASE_URL}/company/{company_number}/filing-history",
                        params={"items_per_page": 15},
                    ),
                    client.get(
                        f"{self._BASE_URL}/company/{company_number}"
                        "/persons-with-significant-control"
                    ),
                    return_exceptions=True,
                )

                raw: dict = {}
                for label, resp in [
                    ("profile", profile_resp),
                    ("officers", officers_resp),
                    ("filing_history", filings_resp),
                    ("persons_with_significant_control", psc_resp),
                ]:
                    if isinstance(resp, Exception):
                        raw[label] = {"error": str(resp)}
                    else:
                        try:
                            resp.raise_for_status()
                            raw[label] = resp.json()
                        except httpx.HTTPStatusError as exc:
                            raw[label] = {"error": f"HTTP {exc.response.status_code}"}

                return SearchModuleResult(raw_data=raw)

        except httpx.HTTPStatusError as exc:
            return SearchModuleResult(
                error=f"Companies House API error {exc.response.status_code}: {exc.response.text}"
            )
        except Exception as exc:
            return SearchModuleResult(error=str(exc))

