import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.src.models.context import SearchContext
from app.src.models.request import AssessmentRequest
from app.src.models.response import (
    CandidateCompany,
    ModuleStatus,
    RiskSummary,
)
from app.src.search_modules.base import BaseSearchModule, SearchModuleResult
from app.src.services.assessment_service import AssessmentService


def _make_job_manager():
    jm = MagicMock()
    jm.set_job_running = Mock()
    jm.fail_job = Mock()
    jm.set_job_ambiguous = Mock()
    jm.set_resolved_context = Mock()
    jm.update_module_status = Mock()
    jm.add_module_result = Mock()
    jm.complete_job = Mock()
    return jm


def _make_llm_service():
    llm = MagicMock()
    llm.parse_module_result = AsyncMock(return_value={"findings": []})
    llm.synthesize_results = AsyncMock(return_value=RiskSummary(
        overall_risk_level="low",
        risk_score=10,
        summary="No significant risks found.",
    ))
    return llm


def _make_candidate(name="Acme Ltd", number="12345678"):
    return CandidateCompany(
        company_name=name,
        registration_number=number,
        jurisdiction="GB",
        source="companies_house",
        warnings=[],
    )


def _make_request(company_name="Acme Ltd", registration_number=None, jurisdiction="GB"):
    return AssessmentRequest(
        company_name=company_name,
        registration_number=registration_number,
        jurisdiction=jurisdiction,
    )


class MockSearchModule(BaseSearchModule):
    module_id = "mock_module"
    module_name = "Mock Module"
    description = "A mock search module for testing"
    output_schema = {"type": "object", "additionalProperties": True}

    async def fetch(self, _context: SearchContext) -> SearchModuleResult:
        return SearchModuleResult(raw_data={})


@pytest.fixture
def job_manager():
    return _make_job_manager()


@pytest.fixture
def llm_service():
    return _make_llm_service()


@pytest.fixture
def assessment_service(job_manager, llm_service):
    return AssessmentService(job_manager=job_manager, llm_service=llm_service)


@pytest.fixture
def search_context():
    return SearchContext(company_name="Acme Ltd", jurisdiction="GB")


class TestValidateOutput:
    def test_valid_data_returns_no_errors(self, assessment_service):
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        assert assessment_service._validate_output({"name": "Acme"}, schema) == []

    def test_missing_required_field_returns_errors(self, assessment_service):
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        assert len(assessment_service._validate_output({}, schema)) > 0

    def test_wrong_type_returns_errors(self, assessment_service):
        schema = {
            "type": "object",
            "properties": {"score": {"type": "integer"}},
            "additionalProperties": False,
        }
        assert len(assessment_service._validate_output({"score": "not-an-int"}, schema)) > 0


class TestRunAssessment:
    @pytest.mark.asyncio
    @patch("app.src.services.assessment_service.get_registry_modules", return_value=[])
    async def test_no_registry_modules_fails_job(self, _, assessment_service, job_manager):
        await assessment_service.run_assessment("job-1", _make_request(jurisdiction="XX"))

        job_manager.fail_job.assert_called_once()
        _, error_msg = job_manager.fail_job.call_args[0]
        assert "No registry module available for jurisdiction 'XX'" in error_msg

    @pytest.mark.asyncio
    @patch("app.src.services.assessment_service.get_registry_modules")
    async def test_no_candidates_found_fails_job(self, mock_get_registry, assessment_service, job_manager):
        registry = MagicMock()
        registry.search_companies = AsyncMock(return_value=[])
        mock_get_registry.return_value = [registry]

        await assessment_service.run_assessment("job-1", _make_request())

        job_manager.fail_job.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.src.services.assessment_service.get_registry_modules")
    async def test_registry_error_fails_job_with_error_detail(self, mock_get_registry, assessment_service, job_manager):
        registry = MagicMock()
        registry.search_companies = AsyncMock(side_effect=Exception("API down"))
        mock_get_registry.return_value = [registry]

        await assessment_service.run_assessment("job-1", _make_request())

        job_manager.fail_job.assert_called_once()
        _, error_msg = job_manager.fail_job.call_args[0]
        assert "API down" in error_msg

    @pytest.mark.asyncio
    @patch("app.src.services.assessment_service.get_registry_modules")
    async def test_multiple_candidates_sets_ambiguous(self, mock_get_registry, assessment_service, job_manager):
        registry = MagicMock()
        registry.search_companies = AsyncMock(return_value=[
            _make_candidate("Acme Ltd", "111"),
            _make_candidate("Acme Holdings Ltd", "222"),
        ])
        mock_get_registry.return_value = [registry]

        await assessment_service.run_assessment("job-1", _make_request(company_name="Acme"))

        job_manager.set_job_ambiguous.assert_called_once()
        job_manager.complete_job.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.src.services.assessment_service.get_all_modules")
    @patch("app.src.services.assessment_service.get_registry_modules")
    async def test_exact_name_match_resolves_ambiguity(self, mock_get_registry, mock_get_modules, assessment_service, job_manager):
        registry = MagicMock()
        registry.search_companies = AsyncMock(return_value=[
            _make_candidate("Acme Ltd", "111"),
            _make_candidate("Acme Holdings Ltd", "222"),
        ])
        mock_get_registry.return_value = [registry]

        module = MockSearchModule()
        module.fetch = AsyncMock(return_value=SearchModuleResult(raw_data={}))
        mock_get_modules.return_value = [module]

        with patch("app.src.services.assessment_service.get_settings") as mock_settings:
            mock_settings.return_value.module_timeout_seconds = 30
            await assessment_service.run_assessment("job-1", _make_request(company_name="Acme Ltd"))

        job_manager.set_job_ambiguous.assert_not_called()
        job_manager.complete_job.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.src.services.assessment_service.get_all_modules")
    @patch("app.src.services.assessment_service.get_registry_modules")
    async def test_all_modules_fail_fails_job(self, mock_get_registry, mock_get_modules, assessment_service, job_manager):
        registry = MagicMock()
        registry.search_companies = AsyncMock(return_value=[_make_candidate()])
        mock_get_registry.return_value = [registry]

        module = MockSearchModule()
        module.fetch = AsyncMock(return_value=SearchModuleResult(error="Source unavailable"))
        mock_get_modules.return_value = [module]

        with patch("app.src.services.assessment_service.get_settings") as mock_settings:
            mock_settings.return_value.module_timeout_seconds = 30
            await assessment_service.run_assessment("job-1", _make_request())

        job_manager.fail_job.assert_called_once()
        job_manager.complete_job.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.src.services.assessment_service.get_all_modules")
    @patch("app.src.services.assessment_service.get_registry_modules")
    async def test_synthesis_failure_fails_job(self, mock_get_registry, mock_get_modules, assessment_service, job_manager, llm_service):
        registry = MagicMock()
        registry.search_companies = AsyncMock(return_value=[_make_candidate()])
        mock_get_registry.return_value = [registry]

        module = MockSearchModule()
        module.fetch = AsyncMock(return_value=SearchModuleResult(raw_data={"data": "ok"}))
        mock_get_modules.return_value = [module]

        llm_service.synthesize_results = AsyncMock(side_effect=RuntimeError("LLM synthesis failed"))

        with patch("app.src.services.assessment_service.get_settings") as mock_settings:
            mock_settings.return_value.module_timeout_seconds = 30
            await assessment_service.run_assessment("job-1", _make_request())

        job_manager.fail_job.assert_called_once()
        _, error_msg = job_manager.fail_job.call_args[0]
        assert "LLM synthesis failed" in error_msg
        job_manager.complete_job.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.src.services.assessment_service.get_all_modules")
    @patch("app.src.services.assessment_service.get_registry_modules")
    async def test_successful_assessment_completes_job(self, mock_get_registry, mock_get_modules, assessment_service, job_manager):
        registry = MagicMock()
        registry.search_companies = AsyncMock(return_value=[_make_candidate()])
        mock_get_registry.return_value = [registry]

        module = MockSearchModule()
        module.fetch = AsyncMock(return_value=SearchModuleResult(raw_data={"data": "ok"}))
        mock_get_modules.return_value = [module]

        with patch("app.src.services.assessment_service.get_settings") as mock_settings:
            mock_settings.return_value.module_timeout_seconds = 30
            await assessment_service.run_assessment("job-1", _make_request())

        job_manager.complete_job.assert_called_once()
        job_manager.fail_job.assert_not_called()


class TestRunModule:
    async def _run(self, service, module, context, timeout=30):
        with patch("app.src.services.assessment_service.get_settings") as mock_settings:
            mock_settings.return_value.module_timeout_seconds = timeout
            return await service._run_module("job-1", module, context)

    @pytest.mark.asyncio
    async def test_timeout_marks_module_failed(self, assessment_service, search_context):
        module = MockSearchModule()
        module.fetch = AsyncMock(return_value=SearchModuleResult(raw_data={}))

        def _timeout(coro, *args, **kwargs):
            coro.close()
            raise asyncio.TimeoutError()

        with patch("app.src.services.assessment_service.asyncio.wait_for", side_effect=_timeout):
            result = await self._run(assessment_service, module, search_context)

        assert result.status == ModuleStatus.FAILED
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_fetch_error_marks_module_failed(self, assessment_service, search_context):
        module = MockSearchModule()
        module.fetch = AsyncMock(return_value=SearchModuleResult(error="Source unavailable"))

        result = await self._run(assessment_service, module, search_context)

        assert result.status == ModuleStatus.FAILED
        assert result.error == "Source unavailable"

    @pytest.mark.asyncio
    async def test_unexpected_exception_marks_module_failed(self, assessment_service, search_context):
        module = MockSearchModule()
        module.fetch = AsyncMock(side_effect=RuntimeError("Unexpected crash"))

        result = await self._run(assessment_service, module, search_context)

        assert result.status == ModuleStatus.FAILED
        assert "Unexpected crash" in result.error

    @pytest.mark.asyncio
    async def test_successful_fetch_marks_module_completed(self, assessment_service, search_context):
        module = MockSearchModule()
        module.fetch = AsyncMock(return_value=SearchModuleResult(raw_data={"key": "val"}))

        result = await self._run(assessment_service, module, search_context)

        assert result.status == ModuleStatus.COMPLETED
        assert result.error is None

    @pytest.mark.asyncio
    async def test_not_skipping_llm_parsing_parses_data_via_llm(self, assessment_service, llm_service, search_context):
        module = MockSearchModule()
        module.skip_llm_parsing = False
        module.fetch = AsyncMock(return_value=SearchModuleResult(raw_data={"direct": True}))

        result = await self._run(assessment_service, module, search_context)

        llm_service.parse_module_result.assert_called_once()
        assert result.status == ModuleStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_skip_llm_parsing_uses_raw_data_directly(self, assessment_service, llm_service, search_context):
        module = MockSearchModule()
        module.skip_llm_parsing = True
        module.fetch = AsyncMock(return_value=SearchModuleResult(raw_data={"direct": True}))

        result = await self._run(assessment_service, module, search_context)

        llm_service.parse_module_result.assert_not_called()
        assert result.status == ModuleStatus.COMPLETED
        assert result.data == {"direct": True}

    @pytest.mark.asyncio
    async def test_llm_parse_error_marks_module_failed(self, assessment_service, llm_service, search_context):
        module = MockSearchModule()
        module.fetch = AsyncMock(return_value=SearchModuleResult(raw_data={"raw": True}))
        llm_service.parse_module_result = AsyncMock(return_value={"error": "LLM failed"})

        result = await self._run(assessment_service, module, search_context)

        assert result.status == ModuleStatus.FAILED
        assert "LLM failed" in result.error
