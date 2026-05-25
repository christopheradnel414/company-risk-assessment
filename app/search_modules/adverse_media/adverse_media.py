import json
import logging
import re
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings
from app.models.context import SearchContext
from app.search_modules.base import BaseSearchModule, SearchModuleResult

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 5

_SYSTEM_PROMPT = (
    "You are a company due diligence analyst specialising in adverse media screening. "
    "Use the web_search tool to research whether the company has been mentioned in "
    "scam reports, fraud allegations, regulatory actions, lawsuits, or negative media coverage. "
    "Run 2-3 targeted searches, then return a single JSON object matching the provided schema. "
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
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Research adverse media for: **{context.company_name}**\n\n"
                    f"Return a JSON object strictly matching this schema:\n{schema_str}"
                ),
            },
        ]

        try:
            for _ in range(_MAX_TOOL_ROUNDS):
                response = await client.chat.completions.create(
                    model=settings.openrouter_model,
                    messages=messages,
                    tools=[{"type": "openrouter:web_search"}],
                )
                choice = response.choices[0]
                msg = choice.message

                if choice.finish_reason == "stop" or not msg.tool_calls:
                    return SearchModuleResult(raw_data=_parse_json(msg.content or "{}"))
                
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                for tc in msg.tool_calls:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "",
                    })

            return SearchModuleResult(
                error="Adverse media search did not complete within the allowed tool rounds"
            )

        except Exception as exc:
            logger.error("Adverse media search failed for '%s': %s", context.company_name, exc)
            return SearchModuleResult(error=str(exc))


def _parse_json(content: str) -> dict:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content).strip()
    return json.loads(content)
