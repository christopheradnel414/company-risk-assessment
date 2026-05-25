import json
import logging
import re
from pathlib import Path

import jsonschema
from openai import AsyncOpenAI

from app.config import get_settings
from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a company due diligence analyst specialising in adverse media screening. "
    "You will be given exact search queries to run using the web_search tool. "
    "Run each query, then consolidate the findings into a single JSON object matching the provided schema. "
    "Return ONLY the JSON object — no markdown fences, no explanation."
)


class AdverseMediaModule(BaseSearchModule):
    module_id = "adverse_media"
    module_name = "Adverse Media"
    description = (
        "Searches the web for scam reports, fraud allegations, regulatory actions, "
        "lawsuits, and negative media coverage about the company."
    )
    jurisdictions = None
    skip_llm_parsing = True
    output_schema = json.loads(
        (Path(__file__).with_suffix(".schema.json")).read_text()
    )

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        settings = get_settings()
        client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

        schema_str = json.dumps(self.output_schema, indent=2)
        max_attempts = 1 + settings.llm_parse_retries
        last_parsed: dict = {}

        for attempt in range(1, max_attempts + 1):
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
                                f'2. "{context.company_name}" investigation OR lawsuit OR fine OR regulatory\n\n'
                                f"Return a JSON object strictly matching this schema:\n{schema_str}"
                            ),
                        },
                    ],
                    tools=[{"type": "openrouter:web_search"}],
                    temperature=0.0,
                )
                last_parsed = _parse_json(response.choices[0].message.content or "{}")
                schema_errors = _validate(last_parsed, self.output_schema)
                if not schema_errors:
                    return SearchModuleResult(raw_data=last_parsed)
                logger.warning(
                    "Adverse media schema validation failed (attempt %d/%d): %s",
                    attempt, max_attempts, schema_errors,
                )
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Adverse media JSON parse failed (attempt %d/%d): %s",
                    attempt, max_attempts, exc,
                )
            except Exception as exc:
                logger.error("Adverse media search failed for '%s': %s", context.company_name, exc)
                return SearchModuleResult(error=str(exc))

        return SearchModuleResult(raw_data=last_parsed)


def _parse_json(content: str) -> dict:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content).strip()
    return json.loads(content)


def _validate(data: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in sorted(validator.iter_errors(data), key=str)]
