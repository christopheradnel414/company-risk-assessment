from fastapi import APIRouter, BackgroundTasks, Request

from app.src.models.request import AssessmentRequest
from app.src.models.response import CreateAssessmentResponse
from app.src.services.assessment_service import AssessmentService
from app.src.services.job_manager import JobManager

router = APIRouter(prefix="/assessments", tags=["Assessments"])


def _job_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


def _assessment_service(request: Request) -> AssessmentService:
    return request.app.state.assessment_service


@router.post(
    "",
    response_model=CreateAssessmentResponse,
    status_code=202,
    summary="Submit a company for background check",
    description="Submit a company for a full background check. The assessment runs asynchronously in the background, allowing you to return immediately and poll for progress.",
)
def create_assessment(
    payload: AssessmentRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> CreateAssessmentResponse:
    job_manager = _job_manager(request)
    assessment_service = _assessment_service(request)

    job_id = job_manager.create_job(payload)
    background_tasks.add_task(assessment_service.run_assessment, job_id, payload)

    return CreateAssessmentResponse(
        job_id=job_id,
        status_url=f"/api/v1/jobs/{job_id}",
    )
