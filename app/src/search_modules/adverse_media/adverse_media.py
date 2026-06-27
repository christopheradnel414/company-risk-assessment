import asyncio
import json
import logging
import re
from pathlib import Path

import jsonschema
from ddgs import DDGS
from openai import AsyncOpenAI

from app.src.config import get_settings
from app.src.models.context import SearchContext
from app.src.search_modules.base import BaseSearchModule, SearchModuleResult

logger = logging.getLogger(__name__)

_SCHEMA = json.loads((Path(__file__).with_suffix(".schema.json")).read_text())
_LLM_RETRY = 3 # the number of retries allowed for LLM parsing
_MAX_RESULTS_PER_QUERY = 5  # DuckDuckGo results fetched per query
_MAX_TOTAL_RESULTS = 20  # cap on deduped results handed to the LLM

# Adverse-media risk terms. Each is run as its own focused query — clean
# single-term queries return far more relevant results than boolean OR strings.
_RISK_TERMS = [
    "scam",
    "fraud",
    "complaint",
    "investigation",
    "lawsuit",
    "fine",
    "regulatory action",
    "sanctions",
]

_SYSTEM_PROMPT = (
    "You are a company due diligence analyst specialising in adverse media screening. "
    "You are given the raw results of web searches about a company. Analyse them and return "
    "a single JSON object that strictly matches the schema below. "
    "Each hit must use the real URL and title taken from the search results — do not invent or omit URLs. "
    "Include at most 5 hits, selecting only the most credible and severe findings. "
    "If the results contain nothing genuinely adverse, return an empty hits list. "
    "Return ONLY the JSON object, no markdown fences, no explanation.\n\n"
    f"Schema:\n{json.dumps(_SCHEMA, indent=2)}"
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

        name = context.company_name
        queries = [f'"{name}" {term}' for term in _RISK_TERMS]

        # This service owns web search: run one focused query per risk term
        # locally via DuckDuckGo (no API key), dedupe, then hand the results to
        # the LLM purely to extract JSON.
        results = await asyncio.gather(
            *(asyncio.to_thread(_search, q, _MAX_RESULTS_PER_QUERY) for q in queries)
        )
        hits = _dedupe(results, _MAX_TOTAL_RESULTS)
        if not hits:
            logger.warning("adverse_media: no search results for '%s'", name)

        user_prompt = (
            f"Company under review: **{name}**\n\n"
            f"Web search results:\n{_format_hits(hits)}\n\n"
            "Return a JSON object strictly matching the schema in the system prompt."
        )

        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        max_attempts = 1 + _LLM_RETRY

        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.chat.completions.create(
                    model=settings.openrouter_model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=4096,
                )
            except Exception as exc:
                logger.error("adverse_media LLM call failed for '%s': %s", name, exc)
                return SearchModuleResult(error=str(exc))

            content = response.choices[0].message.content or "{}"
            try:
                parsed = _parse_json(content)
                errors = _validate(parsed, _SCHEMA)
            except json.JSONDecodeError as exc:
                parsed, errors = None, [f"invalid JSON: {exc}"]

            if parsed is not None and not errors:
                return SearchModuleResult(raw_data=parsed)

            logger.warning(
                "adverse_media invalid output (attempt %d/%d): %s",
                attempt, max_attempts, errors,
            )
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": (
                    f"Your previous reply was not valid: {errors}. "
                    "Return ONLY a single JSON object that strictly matches the schema. "
                    "No markdown fences, no explanation."
                ),
            })

        return SearchModuleResult(error="adverse_media failed to produce a valid response after all retries")


def _search(query: str, max_results: int) -> list[dict]:
    """Run one DuckDuckGo search locally. Returns [] on failure so the LLM can
    still produce a (possibly empty) result rather than the whole module erroring."""
    try:
        return list(DDGS().text(query, max_results=max_results))
    except Exception as exc:  # network / rate-limit
        logger.warning("adverse_media web search failed for %r: %s", query, exc)
        return []


# Ad/tracking redirects that search engines occasionally inject — not real hits.
_AD_URL_MARKERS = ("bing.com/aclick", "duckduckgo.com/y.js", "/aclk?", "googleadservices")


def _dedupe(results: list[list[dict]], limit: int) -> list[dict]:
    """Flatten per-query results into a single list, deduped by URL, capped at `limit`.
    Obvious ad/tracking redirects are dropped."""
    seen: set[str] = set()
    hits: list[dict] = []
    for query_hits in results:
        for hit in query_hits:
            url = hit.get("href")
            if not url or url in seen:
                continue
            if any(marker in url for marker in _AD_URL_MARKERS):
                continue
            seen.add(url)
            hits.append(hit)
            if len(hits) >= limit:
                return hits
    return hits


def _format_hits(hits: list[dict]) -> str:
    """Render deduped DuckDuckGo results into a compact numbered block for the LLM."""
    if not hits:
        return "(no results)"
    return "\n".join(
        f"{i}. {hit.get('title')}\n"
        f"   URL: {hit.get('href')}\n"
        f"   {hit.get('body')}"
        for i, hit in enumerate(hits, 1)
    )


def _parse_json(content: str) -> dict:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content).strip()
    return json.loads(content)


def _validate(data: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in sorted(validator.iter_errors(data), key=str)]
