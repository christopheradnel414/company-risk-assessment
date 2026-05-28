import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.src.models.context import SearchContext
from app.src.models.request import AssessmentRequest
from app.src.models.response import (
    AssessmentResult,
    CandidateCompany,
    JobResponse,
    JobStatus,
    JobSummary,
    ModuleStatus,
    SearchModuleProgress,
    SearchResult,
)


class _Job:
    def __init__(self, job_id: str, request: AssessmentRequest) -> None:
        self.job_id = job_id
        self.request = request
        self.status: JobStatus = JobStatus.PENDING
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.module_statuses: Dict[str, SearchModuleProgress] = {}
        self.finished_module_results: List[SearchResult] = []
        self.resolved_context: Optional[SearchContext] = None
        self.result: Optional[AssessmentResult] = None
        self.candidates: Optional[List[CandidateCompany]] = None
        self.error: Optional[str] = None

    def _query(self) -> SearchContext:
        return SearchContext(
            company_name=self.request.company_name,
            registration_number=self.request.registration_number,
            jurisdiction=self.request.jurisdiction,
        )

    def to_response(self) -> JobResponse:
        return JobResponse(
            job_id=self.job_id,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            completed_at=self.completed_at,
            query=self._query(),
            resolved_context=self.resolved_context,
            progress=list(self.module_statuses.values()),
            finished_module_results=list(self.finished_module_results),
            candidates=self.candidates,
            final_assessment_result=self.result,
            error=self.error,
        )

    def to_summary(self) -> JobSummary:
        return JobSummary(
            job_id=self.job_id,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            completed_at=self.completed_at,
            query=self._query(),
            resolved_context=self.resolved_context,
            progress=list(self.module_statuses.values()),
            candidates=self.candidates,
            error=self.error,
        )


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, _Job] = {}
        self._lock = asyncio.Lock()

    def create_job(self, request: AssessmentRequest) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = _Job(job_id=job_id, request=request)
        return job_id

    async def set_job_running(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.RUNNING
                job.updated_at = datetime.now(timezone.utc)

    async def update_module_status(
        self,
        job_id: str,
        module_id: str,
        module_name: str,
        status: ModuleStatus,
        error: Optional[str] = None,
    ) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            now = datetime.now(timezone.utc)

            if module_id not in job.module_statuses:
                job.module_statuses[module_id] = SearchModuleProgress(
                    module_id=module_id,
                    module_name=module_name,
                    status=status,
                )

            module_status = job.module_statuses[module_id]
            module_status.status = status

            if status == ModuleStatus.RUNNING and module_status.started_at is None:
                module_status.started_at = now
            elif status in (ModuleStatus.COMPLETED, ModuleStatus.FAILED):
                module_status.completed_at = now
                if error:
                    module_status.error = error

            job.updated_at = now

    async def complete_job(self, job_id: str, result: AssessmentResult) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.result = result
                now = datetime.now(timezone.utc)
                job.updated_at = now
                job.completed_at = now

    async def set_job_ambiguous(self, job_id: str, candidates: List[CandidateCompany]) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.AMBIGUOUS
                job.candidates = candidates
                job.updated_at = datetime.now(timezone.utc)

    async def fail_job(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error = error
                now = datetime.now(timezone.utc)
                job.updated_at = now
                job.completed_at = now

    async def set_resolved_context(self, job_id: str, context: SearchContext) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.resolved_context = context
                job.updated_at = datetime.now(timezone.utc)

    async def add_module_result(self, job_id: str, result: SearchResult) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.finished_module_results.append(result)
                job.updated_at = datetime.now(timezone.utc)

    def get_job(self, job_id: str) -> Optional[_Job]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[_Job]:
        return list(self._jobs.values())
