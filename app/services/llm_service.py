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

    async def _chat(
        self, system_prompt: str, user_prompt: str, schema: dict = None, temperature: float = 0.0
    ) -> dict:
        response_format = {"type": "json_schema", "json_schema": {"name": "output", "schema": schema, "strict": True}}
        
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
            temperature=temperature,
        )
        return json.loads(response.choices[0].message.content)

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

    _SYNTHESIS_SCHEMA = {
        "type": "object",
        "required": ["risk_score", "summary"],
        "additionalProperties": False,
        "properties": {
            "risk_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": (
                    "Overall risk score 0–100. "
                    "Use these anchors consistently: "
                    "0–9 = clean (active company, no flags anywhere); "
                    "10–29 = low (minor or unverified concerns); "
                    "30–59 = medium (notable concerns — dissolved status, unresolved complaints, "
                    "adverse media without confirmed fraud); "
                    "60–79 = high (confirmed fraud/scam reports, regulatory action, lawsuit, "
                    "significant adverse media); "
                    "80–100 = critical (confirmed ICIJ leak appearance, criminal prosecution, "
                    "multiple serious flags)."
                ),
            },
            "summary": {
                "type": "string",
                "description": "2–3 sentence narrative conclusion of overall risk",
            },
        },
    }

    _SYNTHESIS_SYSTEM_PROMPT = (
        "You are a senior risk analyst specialising in company due diligence. "
        "You will receive structured findings from multiple independent search modules. "
        "Your task is to synthesise these into a consistent, evidence-based risk score. "
        "Apply the scoring anchors literally and consistently — the same findings should "
        "always produce the same score. Only flag an indicator if there is explicit evidence "
        "for it in the module data; do not speculate."
    )

    async def synthesize_results(
        self,
        company_name: Optional[str],
        registration_number: Optional[str],
        jurisdiction: str,
        search_results: list[SearchResult],
    ) -> RiskSummary:
        results_payload = [
            {
                "module": r.module_name,
                "status": r.status,
                "data": r.data,
                "error": r.error,
            }
            for r in search_results
        ]

        completed = sum(1 for r in search_results if r.status == "completed")
        failed = sum(1 for r in search_results if r.status == "failed")

        user_prompt = (
            f"Assess risk for:\n"
            f"  Company: {company_name or 'Not provided'}\n"
            f"  Registration number: {registration_number or 'Not provided'}\n"
            f"  Jurisdiction: {jurisdiction}\n\n"
            f"Module results ({completed} completed, {failed} failed):\n"
            f"```json\n{json.dumps(results_payload, indent=2, default=str)}\n```\n\n"
            f"Apply the scoring anchors from the schema description exactly. "
            f"If most modules failed and findings are unavailable, set risk_score=50 "
            f"and note the data gap in the summary."
        )

        result = await self._chat(
            self._SYNTHESIS_SYSTEM_PROMPT,
            user_prompt,
            schema=self._SYNTHESIS_SCHEMA,
        )
        score = result["risk_score"]
        if score < 30:
            level = "low"
        elif score < 60:
            level = "medium"
        else:
            level = "high"
        return RiskSummary(
            overall_risk_level=level,
            risk_score=score,
            summary=result.get("summary", ""),
        )
