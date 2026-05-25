import json
from pathlib import Path

from openai import AsyncOpenAI

from app.config import get_settings
from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult

_SYSTEM_PROMPT = (
    "You are a company due diligence analyst specialising in adverse media screening. "
    "You will be given exact search queries to run using the web_search tool. "
    "Run each query, then write a very concise summary of any adverse media found."
)


class AdverseMediaModule(BaseSearchModule):
    module_id = "adverse_media"
    module_name = "Adverse Media"
    description = (
        "Searches the web for scam reports, fraud allegations, regulatory actions, "
        "lawsuits, and negative media coverage about the company."
    )
    jurisdictions = None
    skip_llm_parsing = False
    output_schema = json.loads(
        (Path(__file__).with_suffix(".schema.json")).read_text()
    )

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        settings = get_settings()
        client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

        try:
            response = await client.chat.completions.create(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Research adverse media for: **{context.company_name}**\n\n"
                            f"Run these two searches in order:\n"
                            f'1. "{context.company_name}" scam OR fraud OR complaint\n'
                            f'2. "{context.company_name}" investigation OR lawsuit OR fine OR regulatory'
                        ),
                    },
                ],
                tools=[{"type": "openrouter:web_search"}],
                temperature=0.0,
                max_tokens=4096
            )
            return SearchModuleResult(raw_data=response.choices[0].message.content or "")
        except Exception as exc:
            return SearchModuleResult(error=str(exc))
