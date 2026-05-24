from fastapi import APIRouter, HTTPException, Request

from app.models.response import JobResponse
from app.services.job_manager import JobManager

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _job_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status and results",
    description="""
Retrieve the current status and results of a background check job.

### Job status lifecycle
| Status | Meaning |
|--------|---------|
| `pending` | Job is queued and hasn't started yet |
| `running` | Searches are in progress |
| `completed` | All searches done; full results available in `result` |
| `failed` | Unrecoverable error — check server logs |

### Module status lifecycle
| Status | Meaning |
|--------|---------|
| `pending` | Module not yet started |
| `running` | Module is fetching / processing data |
| `completed` | Module finished successfully |
| `failed` | Module encountered an error (others continue regardless) |

> Individual module failures do **not** fail the overall job — the LLM synthesis
> works with whichever modules succeeded.
""",
)
async def get_job(job_id: str, request: Request) -> JobResponse:
    job = _job_manager(request).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job.to_response()


@router.get(
    "",
    response_model=list[JobResponse],
    summary="List all assessment jobs",
    description="Returns all submitted jobs, most recent first. Useful for monitoring and debugging.",
)
async def list_jobs(request: Request) -> list[JobResponse]:
    jobs = _job_manager(request).list_jobs()
    return [job.to_response() for job in reversed(jobs)]
