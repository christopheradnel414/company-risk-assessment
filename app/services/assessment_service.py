import asyncio
import logging
from typing import Any, Optional

import jsonschema

from app.config import get_settings
from app.models.context import SearchContext
from app.models.request import AssessmentRequest
from app.models.response import AssessmentResult, ModuleStatus, SearchResult
from app.registry_modules.base import BaseRegistryModule
from app.registry_modules.modules import get_registry_modules
from app.search_modules.base import BaseSearchModule
from app.search_modules.modules import get_all_modules
from app.services.job_manager import JobManager
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AssessmentService:
    def __init__(self, job_manager: JobManager, llm_service: LLMService) -> None:
        self._job_manager = job_manager
        self._llm_service = llm_service

    # ── Schema validation ──────────────────────────────────────────────────────

    @staticmethod
    def _validate_output(data: Any, schema: Optional[dict]) -> list[str]:
        """Validate data against a JSON Schema; returns a list of error messages."""
        if not schema or not isinstance(data, dict):
            return []
        validator = jsonschema.Draft7Validator(schema)
        return [e.message for e in sorted(validator.iter_errors(data), key=str)]

    # ── Single-module execution ────────────────────────────────────────────────

    async def _run_module(
        self,
        job_id: str,
        module: BaseSearchModule,
        context: SearchContext,
    ) -> SearchResult:
        timeout = float(get_settings().module_timeout_seconds)

        await self._job_manager.update_module_status(
            job_id, module.module_id, module.module_name, ModuleStatus.RUNNING
        )

        try:
            raw_result = await asyncio.wait_for(
                module.fetch(context),
                timeout=timeout,
            )

            if raw_result.error:
                await self._job_manager.update_module_status(
                    job_id, module.module_id, module.module_name,
                    ModuleStatus.FAILED, error=raw_result.error,
                )
                return SearchResult(
                    module_id=module.module_id,
                    module_name=module.module_name,
                    status=ModuleStatus.FAILED,
                    error=raw_result.error,
                )

            if module.skip_llm_parsing:
                parsed = raw_result.raw_data if isinstance(raw_result.raw_data, dict) else {}
            else:
                parsed = await self._llm_service.parse_module_result(module, raw_result)

            schema_errors = self._validate_output(parsed, module.output_schema)
            if schema_errors:
                logger.warning(
                    "Schema validation failed for module '%s': %s",
                    module.module_id, schema_errors,
                )

            await self._job_manager.update_module_status(
                job_id, module.module_id, module.module_name, ModuleStatus.COMPLETED
            )
            return SearchResult(
                module_id=module.module_id,
                module_name=module.module_name,
                status=ModuleStatus.COMPLETED,
                data=parsed,
                schema_errors=schema_errors or None,
            )

        except asyncio.TimeoutError:
            error_msg = f"Module timed out after {timeout:.0f}s"
            logger.warning("Module '%s' timed out for job %s", module.module_id, job_id)
            await self._job_manager.update_module_status(
                job_id, module.module_id, module.module_name,
                ModuleStatus.FAILED, error=error_msg,
            )
            return SearchResult(
                module_id=module.module_id,
                module_name=module.module_name,
                status=ModuleStatus.FAILED,
                error=error_msg,
            )
        except Exception as exc:
            error_msg = str(exc)
            logger.error(
                "Unexpected error in module '%s' for job %s: %s",
                module.module_id, job_id, error_msg,
            )
            await self._job_manager.update_module_status(
                job_id, module.module_id, module.module_name,
                ModuleStatus.FAILED, error=error_msg,
            )
            return SearchResult(
                module_id=module.module_id,
                module_name=module.module_name,
                status=ModuleStatus.FAILED,
                error=error_msg,
            )

    # ── Registry disambiguation ────────────────────────────────────────────────

    async def _disambiguate(
        self,
        registry_modules: list[BaseRegistryModule],
        context: SearchContext,
    ) -> list:
        """
        Run all registry modules in parallel and merge candidates.
        Deduplicates by registration_number. Returns empty list on total failure.
        """
        results = await asyncio.gather(
            *[m.search_companies(context) for m in registry_modules],
            return_exceptions=True,
        )
        seen: set[str] = set()
        candidates = []
        for item in results:
            if isinstance(item, Exception):
                logger.warning("Registry module error during disambiguation: %s", item)
                continue
            for c in item:
                if c.registration_number not in seen:
                    seen.add(c.registration_number)
                    candidates.append(c)
        return candidates

    # ── Full assessment orchestration ──────────────────────────────────────────

    async def run_assessment(self, job_id: str, request: AssessmentRequest) -> None:
        try:
            await self._job_manager.set_job_running(job_id)

            jurisdiction = request.jurisdiction
            context = SearchContext(
                company_name=request.company_name,
                registration_number=request.registration_number,
                jurisdiction=jurisdiction,
            )

            # ── Phase 1: registry disambiguation ──────────────────────────────
            registry_modules = get_registry_modules(jurisdiction)
            registry_warnings: list[str] = []

            if registry_modules:
                candidates = await self._disambiguate(registry_modules, context)

                if len(candidates) == 0:
                    await self._job_manager.fail_job(
                        job_id,
                        f"No company found in the registry for "
                        f"name='{request.company_name}', "
                        f"number='{request.registration_number}'.",
                    )
                    return

                if len(candidates) > 1:
                    logger.info(
                        "Job %s — ambiguous: %d candidates found", job_id, len(candidates)
                    )
                    await self._job_manager.set_job_ambiguous(job_id, candidates)
                    return

                # Exactly 1 match — enrich context with canonical data
                match = candidates[0]
                logger.info(
                    "Job %s — resolved to '%s' (%s)",
                    job_id, match.company_name, match.registration_number,
                )
                registry_warnings = match.warnings or []
                context = SearchContext(
                    company_name=match.company_name,
                    registration_number=match.registration_number,
                    jurisdiction=match.jurisdiction,
                )

            # ── Phase 2: search modules ────────────────────────────────────────
            modules = get_all_modules(jurisdiction)

            for module in modules:
                await self._job_manager.update_module_status(
                    job_id, module.module_id, module.module_name, ModuleStatus.PENDING
                )

            all_results = await self._gather_modules(job_id, modules, context)

            if all(r.status == ModuleStatus.FAILED for r in all_results):
                failed_names = ", ".join(r.module_name for r in all_results)
                await self._job_manager.fail_job(
                    job_id, f"All search modules failed: {failed_names}"
                )
                return

            risk_summary = await self._llm_service.synthesize_results(
                company_name=request.company_name,
                registration_number=request.registration_number,
                jurisdiction=jurisdiction,
                search_results=all_results,
            )

            await self._job_manager.complete_job(
                job_id,
                AssessmentResult(
                    company_name=match.company_name,
                    registration_number=match.registration_number,
                    jurisdiction=jurisdiction,
                    search_results=all_results,
                    risk_summary=risk_summary,
                    warnings=registry_warnings,
                ),
            )

        except Exception as exc:
            logger.error("Assessment job %s failed with unhandled error: %s", job_id, exc)
            await self._job_manager.fail_job(job_id, str(exc))

    async def _gather_modules(
        self,
        job_id: str,
        modules: list[BaseSearchModule],
        context: SearchContext,
    ) -> list[SearchResult]:
        """Run all modules in parallel; normalise any escaped exceptions."""
        raw = await asyncio.gather(
            *[self._run_module(job_id, m, context) for m in modules],
            return_exceptions=True,
        )
        results: list[SearchResult] = []
        for i, item in enumerate(raw):
            if isinstance(item, Exception):
                module = modules[i]
                logger.error("Unhandled exception from '%s': %s", module.module_id, item)
                results.append(
                    SearchResult(
                        module_id=module.module_id,
                        module_name=module.module_name,
                        status=ModuleStatus.FAILED,
                        error=str(item),
                    )
                )
            else:
                results.append(item)
        return results
