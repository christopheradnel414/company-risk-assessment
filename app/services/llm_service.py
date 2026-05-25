import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.models.response import RiskSummary, SearchResult
from app.search_modules.base import BaseSearchModule, SearchModuleResult

logger = logging.getLogger(__name__)


class LLMService:
    """Wraps OpenRouter API calls for per-module parsing and final synthesis."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.openrouter_model
        self._client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _chat(
        self, system_prompt: str, user_prompt: str, schema: Optional[dict] = None
    ) -> dict:
        response_format = (
            {"type": "json_schema", "json_schema": {"name": "output", "schema": schema, "strict": True}}
            if schema
            else {"type": "json_object"}
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
            temperature=0.0,
        )
        return json.loads(response.choices[0].message.content)

    # ── Public interface ───────────────────────────────────────────────────────

    async def parse_module_result(
        self,
        module: BaseSearchModule,
        raw_result: SearchModuleResult,
    ) -> dict:
        if raw_result.error:
            return {"error": raw_result.error}

        user_prompt = (
            f"Parse the following raw data from **{module.module_name}** "
            f"and extract all relevant company information.\n\n"
            f"Raw data:\n```\n{json.dumps(raw_result.raw_data, indent=2, default=str)}\n```"
        )

        try:
            return await self._chat(module.system_prompt, user_prompt, schema=module.output_schema)
        except Exception as exc:
            logger.error("LLM parsing failed for module '%s': %s", module.module_id, exc)
            return {"error": f"LLM parsing failed: {exc}"}

    async def synthesize_results(
        self,
        company_name: Optional[str],
        registration_number: Optional[str],
        jurisdiction: str,
        search_results: list[SearchResult],
    ) -> tuple[RiskSummary, str]:
        """
        Generate an overall risk assessment from all completed module results.
        Returns RiskSummary.
        """
        results_payload = [
            {
                "module": r.module_name,
                "status": r.status,
                "data": r.data,
                "error": r.error,
            }
            for r in search_results
        ]

        system_prompt = (
            "You are a senior risk analyst specialising in company due diligence. "
            "Based on research findings from multiple sources, produce a comprehensive, "
            "evidence-based risk assessment in JSON format."
        )

        output_schema = {
            "overall_risk_level": "high | medium | low | unknown",
            "nagative_indicators": ["specific concerning indicators with brief context"],
            "positive_indicators": ["factors that reduce risk or confirm legitimacy"],
        }

        user_prompt = (
            f"Perform a comprehensive risk assessment for:\n"
            f"  Company Name: {company_name or 'Not provided'}\n"
            f"  Registration Number: {registration_number or 'Not provided'}\n"
            f"  Jurisdiction: {jurisdiction}\n\n"
            f"Search findings from {len(search_results)} modules:\n"
            f"```json\n{json.dumps(results_payload, indent=2, default=str)}\n```\n\n"
            f"Return a JSON object matching this structure:\n"
            f"{json.dumps(output_schema, indent=2)}\n\n"
            f"If critical data is missing or modules failed, reflect this uncertainty "
            f"in your and risk level."
        )

        try:
            result = await self._chat(system_prompt, user_prompt)

            risk_summary = RiskSummary(
                overall_risk_level=result.get("overall_risk_level", "unknown"),
                negative_indicators=result.get("negative_indicators", []),
                positive_indicators=result.get("positive_indicators", [])
            )
            return risk_summary

        except Exception as exc:
            logger.error("LLM synthesis failed: %s", exc)
            fallback = RiskSummary(
                overall_risk_level="unknown",
                negative_indicators=[],
                positive_indicators=[]
            )
            return fallback, f"Risk synthesis failed: {exc}"
