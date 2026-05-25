import json
import logging
from pathlib import Path

import httpx

from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult

logger = logging.getLogger(__name__)

_SEARCH_LIMIT = 10

class ICIJOffshoreLeaksModule(BaseSearchModule):
    module_id = "icij_offshore_leaks"
    module_name = "ICIJ Offshore Leaks"
    description = (
        "Searches the ICIJ Offshore Leaks database — Panama Papers, Pandora Papers, "
        "Paradise Papers, Bahamas Leaks, and Offshore Leaks."
    )
    jurisdictions = None
    skip_llm_parsing = False
    output_schema = json.loads(
        (Path(__file__).with_suffix(".schema.json")).read_text()
    )

    system_prompt = (
        "You are an investigative analyst specialising in offshore financial structures. "
        "You are given reconciliation results from the ICIJ Offshore Leaks database. "
        "Each result has a name, description (which contains the dataset name), score (0-100), and match flag. "
        "The score reflects name similarity only — a generic word like 'LIMITED' shared between two unrelated companies can produce a high score. "
        "Use the score as a signal, but apply your own judgement: compare the full result name against the queried company name and only set is_mentioned_in_leaks=true if you are confident it is genuinely the same entity. "
        "Likewise, only include an entity in entities_found if you judge it to be a plausible match, regardless of score threshold. "
        "Extract the dataset name from the description (e.g. 'Panama Papers', 'Pandora Papers'). "
        "Construct source_url as https://offshoreleaks.icij.org/nodes/{id}."
    )

    _BASE_URL = "https://offshoreleaks.icij.org/api/v1"

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        query = context.company_name
        if not query:
            return SearchModuleResult(error="Company name is required")

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{self._BASE_URL}/reconcile",
                    json={"query": query, "type": "Entity", "limit": _SEARCH_LIMIT},
                    headers={"Accept": "application/json"},
                )

            resp.raise_for_status()
            results = resp.json().get("result", [])
            logger.info("ICIJ reconcile for '%s' returned %d result(s)", query, len(results))
            return SearchModuleResult(raw_data={"queried_company": query, "results": results})

        except httpx.TimeoutException:
            return SearchModuleResult(error="ICIJ search timed out")
        except Exception as exc:
            logger.error("ICIJ search failed for '%s': %s", query, exc)
            return SearchModuleResult(error=str(exc))
