import asyncio
import json
from pathlib import Path

import httpx

from app.src.config import get_settings
from app.src.models.context import SearchContext
from app.src.search_modules.base import BaseSearchModule, SearchModuleResult


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

    def _parse_resp(self, resp) -> dict:
        if isinstance(resp, Exception):
            return {"error": str(resp)}
        try:
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return {"error": f"HTTP {exc.response.status_code}"}

    def _filter(self, data, schema: dict, defs: dict):
        if "$ref" in schema:
            schema = defs.get(schema["$ref"].split("/")[-1], {})
        if schema.get("type") == "object" and isinstance(data, dict) and "error" not in data:
            props = schema.get("properties", {})
            return {k: self._filter(v, props[k], defs) for k, v in data.items() if k in props}
        if schema.get("type") == "array" and isinstance(data, list):
            return [self._filter(item, schema.get("items", {}), defs) for item in data]
        return data

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        settings = get_settings()
        api_key = settings.companies_house_api_key

        if not api_key:
            return SearchModuleResult(
                error="Companies House API key not configured. Set COMPANIES_HOUSE_API_KEY in .env"
            )
        if not context.registration_number:
            return SearchModuleResult(error="Company registration number is required")

        try:
            async with httpx.AsyncClient(auth=(api_key, ""), timeout=30.0) as client:
                base = f"{self._BASE_URL}/company/{context.registration_number}"
                responses = await asyncio.gather(
                    client.get(base),
                    client.get(f"{base}/officers"),
                    client.get(f"{base}/filing-history", params={"items_per_page": 15}),
                    client.get(f"{base}/persons-with-significant-control"),
                    return_exceptions=True,
                )
                raw = dict(zip(
                    ("profile", "officers", "filing_history", "persons_with_significant_control"),
                    (self._parse_resp(r) for r in responses),
                ))

                appt_officers = []
                for officer in (raw.get("officers") or {}).get("items") or []:
                    if path := ((officer.get("links") or {}).get("officer") or {}).get("appointments"):
                        appt_officers.append((officer, path))

                if appt_officers:
                    appt_responses = await asyncio.gather(
                        *(client.get(f"{self._BASE_URL}{path}") for _, path in appt_officers),
                        return_exceptions=True,
                    )
                    for (officer, _), appt_resp in zip(appt_officers, appt_responses):
                        officer["appointments"] = self._parse_resp(appt_resp)

                defs = self.output_schema.get("definitions", {})
                props = self.output_schema.get("properties", {})
                raw = {k: self._filter(v, props.get(k, {}), defs) for k, v in raw.items()}

                return SearchModuleResult(raw_data=raw)

        except httpx.HTTPStatusError as exc:
            return SearchModuleResult(
                error=f"Companies House API error {exc.response.status_code}: {exc.response.text}"
            )
        except Exception as exc:
            return SearchModuleResult(error=str(exc))
