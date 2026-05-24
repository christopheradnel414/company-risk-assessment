import asyncio
import logging

from app.config import get_settings
from app.models.context import SearchContext
from app.models.request import AssessmentRequest
from app.models.response import AssessmentResult, ModuleStatus, SearchResult
from app.search_modules.base import BaseSearchModule
from app.search_modules.registry import get_all_modules
from app.services.job_manager import JobManager
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AssessmentService:
    def __init__(self, job_manager: JobManager, llm_service: LLMService) -> None:
        self._job_manager = job_manager
        self._llm_service = llm_service

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

            parsed = await self._llm_service.parse_module_result(module, raw_result)

            await self._job_manager.update_module_status(
                job_id, module.module_id, module.module_name, ModuleStatus.COMPLETED
            )
            return SearchResult(
                module_id=module.module_id,
                module_name=module.module_name,
                status=ModuleStatus.COMPLETED,
                data=parsed,
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

    # ── Full assessment orchestration ──────────────────────────────────────────

    async def run_assessment(self, job_id: str, request: AssessmentRequest) -> None:
        try:
            await self._job_manager.set_job_running(job_id)

            jurisdiction = request.jurisdiction
            modules = get_all_modules(jurisdiction)

            for module in modules:
                await self._job_manager.update_module_status(
                    job_id, module.module_id, module.module_name, ModuleStatus.PENDING
                )

            context = SearchContext(
                company_name=request.company_name,
                registration_number=request.registration_number,
                jurisdiction=jurisdiction,
            )

            all_results = await self._gather_modules(job_id, modules, context)

            risk_summary, conclusion = await self._llm_service.synthesize_results(
                company_name=request.company_name,
                registration_number=request.registration_number,
                jurisdiction=jurisdiction,
                search_results=all_results,
            )

            await self._job_manager.complete_job(
                job_id,
                AssessmentResult(
                    company_name=request.company_name,
                    registration_number=request.registration_number,
                    jurisdiction=jurisdiction,
                    search_results=all_results,
                    risk_summary=risk_summary,
                    search_conclusion=conclusion,
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
