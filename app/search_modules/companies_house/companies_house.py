import asyncio
import json
from pathlib import Path

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
    skip_llm_parsing = True
    output_schema = json.loads(
        (Path(__file__).with_suffix(".schema.json")).read_text()
    )

    _BASE_URL = "https://api.company-information.service.gov.uk"

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
                    return SearchModuleResult(error="Company registration number is required")

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
