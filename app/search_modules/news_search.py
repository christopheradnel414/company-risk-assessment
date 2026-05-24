import asyncio

from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult


class NewsSearchModule(BaseSearchModule):
    module_id = "news_search"
    module_name = "News & Media Coverage"
    description = (
        "Searches recent news articles and media coverage about the company "
        "using DuckDuckGo News (no API key required)."
    )
    jurisdictions = None  # global
    module_tier = "search"

    output_schema = {
        "type": "object",
        "properties": {
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "date": {"type": ["string", "null"]},
                        "snippet": {"type": "string"},
                        "source": {"type": "string"},
                        "sentiment": {
                            "type": "string",
                            "enum": ["positive", "negative", "neutral"],
                        },
                        "relevance": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "How relevant this article is to the specific company",
                        },
                        "topics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Key topics e.g. funding, leadership, scandal",
                        },
                    },
                },
            },
            "overall_media_sentiment": {
                "type": "string",
                "enum": ["positive", "negative", "neutral", "mixed"],
            },
            "key_topics": {"type": "array", "items": {"type": "string"}},
            "notable_events": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Significant events e.g. acquisitions, layoffs, leadership changes",
            },
        },
    }

    system_prompt = (
        "You are a media analyst. Analyse news articles about the company and extract: "
        "sentiment per article, key topics, notable events, and overall media sentiment. "
        "Mark articles as low relevance if they are clearly not about this specific company."
    )

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        if not context.company_name:
            return SearchModuleResult(error="Company name is required for news search")

        query = f'"{context.company_name}" news'

        try:
            from duckduckgo_search import DDGS

            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(DDGS().news(query, max_results=15)),
            )
            return SearchModuleResult(raw_data={"query": query, "articles": results})

        except Exception as exc:
            return SearchModuleResult(error=f"News search failed: {exc}")
