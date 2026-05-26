import pytest

from app.src.models.context import SearchContext
from app.src.models.request import AssessmentRequest
from app.src.models.response import (
    AssessmentResult,
    CandidateCompany,
    JobStatus,
    ModuleStatus,
    RiskSummary,
    SearchResult,
)
from app.src.services.job_manager import JobManager


@pytest.fixture
def job_manager():
    return JobManager()


@pytest.fixture
def assessment_request():
    return AssessmentRequest(company_name="Acme Ltd", jurisdiction="GB")


@pytest.fixture
def job_id(job_manager, assessment_request):
    return job_manager.create_job(assessment_request)


@pytest.fixture
def assessment_result():
    return AssessmentResult(
        company_name="Acme Ltd",
        registration_number="12345678",
        jurisdiction="GB",
        risk_summary=RiskSummary(overall_risk_level="low", risk_score=10, summary="Clean."),
        warnings=[],
    )


class TestCreateAndRetrieve:
    def test_create_job_returns_string_id(self, job_manager, assessment_request):
        job_id = job_manager.create_job(assessment_request)
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    def test_created_job_is_retrievable(self, job_manager, job_id):
        assert job_manager.get_job(job_id) is not None

    def test_created_job_starts_as_pending(self, job_manager, job_id):
        job = job_manager.get_job(job_id)
        assert job.status == JobStatus.PENDING

    def test_get_job_returns_none_for_unknown_id(self, job_manager):
        assert job_manager.get_job("nonexistent") is None

    def test_list_jobs_returns_all_created_jobs(self, job_manager, assessment_request):
        id1 = job_manager.create_job(assessment_request)
        id2 = job_manager.create_job(assessment_request)

        job_ids = {j.job_id for j in job_manager.list_jobs()}
        assert id1 in job_ids
        assert id2 in job_ids

    def test_list_jobs_returns_empty_when_no_jobs(self, job_manager):
        assert job_manager.list_jobs() == []


class TestSetJobRunning:
    @pytest.mark.asyncio
    async def test_transitions_status_to_running(self, job_manager, job_id):
        await job_manager.set_job_running(job_id)
        assert job_manager.get_job(job_id).status == JobStatus.RUNNING

    @pytest.mark.asyncio
    async def test_updates_updated_at(self, job_manager, job_id):
        before = job_manager.get_job(job_id).updated_at
        await job_manager.set_job_running(job_id)
        assert job_manager.get_job(job_id).updated_at >= before


class TestFailJob:
    @pytest.mark.asyncio
    async def test_transitions_status_to_failed(self, job_manager, job_id):
        await job_manager.fail_job(job_id, "Something broke")
        assert job_manager.get_job(job_id).status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_sets_error_message(self, job_manager, job_id):
        await job_manager.fail_job(job_id, "Something broke")
        assert job_manager.get_job(job_id).error == "Something broke"

    @pytest.mark.asyncio
    async def test_sets_completed_at(self, job_manager, job_id):
        await job_manager.fail_job(job_id, "error")
        assert job_manager.get_job(job_id).completed_at is not None


class TestCompleteJob:
    @pytest.mark.asyncio
    async def test_transitions_status_to_completed(self, job_manager, job_id, assessment_result):
        await job_manager.complete_job(job_id, assessment_result)
        assert job_manager.get_job(job_id).status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_stores_result(self, job_manager, job_id, assessment_result):
        await job_manager.complete_job(job_id, assessment_result)
        assert job_manager.get_job(job_id).result == assessment_result

    @pytest.mark.asyncio
    async def test_sets_completed_at(self, job_manager, job_id, assessment_result):
        await job_manager.complete_job(job_id, assessment_result)
        assert job_manager.get_job(job_id).completed_at is not None


class TestSetJobAmbiguous:
    @pytest.fixture
    def candidates(self):
        return [
            CandidateCompany(
                company_name="Acme Ltd",
                registration_number="111",
                jurisdiction="GB",
                source="companies_house",
                warnings=[],
            )
        ]

    @pytest.mark.asyncio
    async def test_transitions_status_to_ambiguous(self, job_manager, job_id, candidates):
        await job_manager.set_job_ambiguous(job_id, candidates)
        assert job_manager.get_job(job_id).status == JobStatus.AMBIGUOUS

    @pytest.mark.asyncio
    async def test_stores_candidates(self, job_manager, job_id, candidates):
        await job_manager.set_job_ambiguous(job_id, candidates)
        assert job_manager.get_job(job_id).candidates == candidates


class TestSetResolvedContext:
    @pytest.mark.asyncio
    async def test_stores_resolved_context(self, job_manager, job_id):
        context = SearchContext(company_name="Acme Ltd", registration_number="123", jurisdiction="GB")
        await job_manager.set_resolved_context(job_id, context)
        assert job_manager.get_job(job_id).resolved_context == context


class TestAddModuleResult:
    @pytest.mark.asyncio
    async def test_appends_result(self, job_manager, job_id):
        search_result = SearchResult(module_id="m1", module_name="M1", status=ModuleStatus.COMPLETED)
        await job_manager.add_module_result(job_id, search_result)
        assert search_result in job_manager.get_job(job_id).finished_module_results

    @pytest.mark.asyncio
    async def test_accumulates_multiple_results(self, job_manager, job_id):
        r1 = SearchResult(module_id="m1", module_name="M1", status=ModuleStatus.COMPLETED)
        r2 = SearchResult(module_id="m2", module_name="M2", status=ModuleStatus.FAILED)

        await job_manager.add_module_result(job_id, r1)
        await job_manager.add_module_result(job_id, r2)

        results = job_manager.get_job(job_id).finished_module_results
        assert len(results) == 2


class TestUpdateModuleStatus:
    @pytest.mark.asyncio
    async def test_creates_module_status_if_not_exists(self, job_manager, job_id):
        await job_manager.update_module_status(job_id, "mod_1", "Module One", ModuleStatus.PENDING)
        assert "mod_1" in job_manager.get_job(job_id).module_statuses

    @pytest.mark.asyncio
    async def test_sets_started_at_on_running(self, job_manager, job_id):
        await job_manager.update_module_status(job_id, "mod_1", "Module One", ModuleStatus.RUNNING)
        assert job_manager.get_job(job_id).module_statuses["mod_1"].started_at is not None

    @pytest.mark.asyncio
    async def test_does_not_overwrite_started_at_on_second_running_call(self, job_manager, job_id):
        await job_manager.update_module_status(job_id, "mod_1", "Module One", ModuleStatus.RUNNING)
        first_started_at = job_manager.get_job(job_id).module_statuses["mod_1"].started_at
        await job_manager.update_module_status(job_id, "mod_1", "Module One", ModuleStatus.RUNNING)
        assert job_manager.get_job(job_id).module_statuses["mod_1"].started_at == first_started_at

    @pytest.mark.asyncio
    async def test_sets_completed_at_on_completed(self, job_manager, job_id):
        await job_manager.update_module_status(job_id, "mod_1", "Module One", ModuleStatus.COMPLETED)
        assert job_manager.get_job(job_id).module_statuses["mod_1"].completed_at is not None

    @pytest.mark.asyncio
    async def test_sets_completed_at_on_failed(self, job_manager, job_id):
        await job_manager.update_module_status(job_id, "mod_1", "Module One", ModuleStatus.FAILED)
        assert job_manager.get_job(job_id).module_statuses["mod_1"].completed_at is not None

    @pytest.mark.asyncio
    async def test_stores_error_message_on_failed(self, job_manager, job_id):
        await job_manager.update_module_status(
            job_id, "mod_1", "Module One", ModuleStatus.FAILED, error="Timed out"
        )
        assert job_manager.get_job(job_id).module_statuses["mod_1"].error == "Timed out"
