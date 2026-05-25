import json
import logging
import re
from pathlib import Path

import jsonschema
from openai import AsyncOpenAI

from app.src.config import get_settings
from app.src.models.context import SearchContext
from app.src.search_modules.base import BaseSearchModule, SearchModuleResult

logger = logging.getLogger(__name__)

_SCHEMA = json.loads((Path(__file__).with_suffix(".schema.json")).read_text())
_SCHEMA_STR = json.dumps(_SCHEMA, indent=2)
_LLM_PARSE_RETRY = 2

_SYSTEM_PROMPT = (
    "You are a company due diligence analyst specialising in adverse media screening. "
    "Use the web_search tool to run the provided queries, then return a single JSON object "
    "that strictly matches the schema below. "
    "Each hit must include the real URL and title from the search result — do not invent or omit URLs. "
    "Return ONLY the JSON object, no markdown fences, no explanation.\n\n"
    f"Schema:\n{_SCHEMA_STR}"
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
    output_schema = _SCHEMA

    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        settings = get_settings()
        client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

        user_prompt = (
            f"Research adverse media for: **{context.company_name}**\n\n"
            f"Run these two searches in order:\n"
            f'1. "{context.company_name}" scam OR fraud OR complaint\n'
            f'2. "{context.company_name}" investigation OR lawsuit OR fine OR regulatory\n\n'
            f"Return a JSON object strictly matching the schema in the system prompt."
        )

        max_attempts = 1 + _LLM_PARSE_RETRY
        last_parsed: dict = {}

        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.chat.completions.create(
                    model=settings.openrouter_model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    tools=[{"type": "openrouter:web_search"}],
                    temperature=0.0,
                    max_tokens=4096,
                )
                content = response.choices[0].message.content or "{}"
                last_parsed = _parse_json(content)
                errors = _validate(last_parsed, _SCHEMA)
                if not errors:
                    return SearchModuleResult(raw_data=last_parsed)
                logger.warning(
                    "adverse_media schema validation failed (attempt %d/%d): %s",
                    attempt, max_attempts, errors,
                )
            except json.JSONDecodeError as exc:
                logger.warning(
                    "adverse_media JSON parse failed (attempt %d/%d): %s",
                    attempt, max_attempts, exc,
                )
            except Exception as exc:
                logger.error("adverse_media search failed for '%s': %s", context.company_name, exc)
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
