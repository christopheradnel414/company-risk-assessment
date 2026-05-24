import asyncio

from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult

_QUERY_SUFFIXES = [
    "scam fraud",
    "complaint investigation",
    "lawsuit legal action court",
    "regulatory fine penalty",
]


class AdverseMediaModule(BaseSearchModule):
    module_id = "adverse_media"
    module_name = "Adverse Media & Fraud Search"
    description = (
        "Searches for scam reports, fraud allegations, customer complaints, "
        "lawsuits, and regulatory investigations using targeted DuckDuckGo queries."
    )
    jurisdictions = None  # global
    module_tier = "search"

    output_schema = {
        "type": "object",
        "properties": {
            "adverse_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "date": {"type": ["string", "null"]},
                        "snippet": {"type": "string"},
                        "finding_type": {
                            "type": "string",
                            "description": (
                                "e.g. scam, fraud, complaint, lawsuit, "
                                "regulatory_action, investigation"
                            ),
                        },
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "source_credibility": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": (
                                "high = established news/regulatory body, "
                                "medium = review site, "
                                "low = forum/blog"
                            ),
                        },
                    },
                },
            },
            "risk_indicators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concise list of specific risk signals found",
            },
            "overall_adverse_risk": {
                "type": "string",
                "enum": ["high", "medium", "low", "none"],
            },
            "summary": {"type": "string"},
        },
    }

    system_prompt = (
        "You are a risk analyst specialising in adverse media screening. "
        "Analyse the search results for credible negative information about this company. "
        "Focus on scam/fraud allegations, legal proceedings, regulatory action, and systemic complaints. "
        "Discard results that are clearly about a different company with a similar name. "
        "Rate severity and source credibility independently."
    )

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        if not context.company_name:
            return SearchModuleResult(error="Company name is required for adverse media search")

        try:
            from duckduckgo_search import DDGS

            loop = asyncio.get_running_loop()
            all_results: list[dict] = []

            for suffix in _QUERY_SUFFIXES:
                query = f'"{context.company_name}" {suffix}'
                results = await loop.run_in_executor(
                    None,
                    lambda q=query: list(DDGS().text(q, max_results=5)),
                )
                all_results.extend(results)

            # Deduplicate by URL
            seen: set[str] = set()
            unique: list[dict] = []
            for item in all_results:
                url = item.get("href", "")
                if url not in seen:
                    seen.add(url)
                    unique.append(item)

            return SearchModuleResult(raw_data={"search_results": unique})

        except Exception as exc:
            return SearchModuleResult(error=f"Adverse media search failed: {exc}")
