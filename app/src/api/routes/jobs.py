from fastapi import APIRouter, HTTPException, Request

from app.src.models.response import JobResponse, JobSummary
from app.src.services.job_manager import JobManager

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _job_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status and results",
    description="Retrieve the current status and results of a background check job.",
)
def get_job(job_id: str, request: Request) -> JobResponse:
    job = _job_manager(request).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job.to_response()


@router.get(
    "",
    response_model=list[JobSummary],
    summary="List all assessment jobs",
    description="Returns all submitted jobs, most recent first. Useful for monitoring and debugging.",
)
def list_jobs(request: Request) -> list[JobSummary]:
    jobs = _job_manager(request).list_jobs()
    return [job.to_summary() for job in reversed(jobs)]
