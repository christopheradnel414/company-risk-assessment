import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.src.api.dependencies import verify_api_key
from app.src.api.routes import assessment, jobs
from app.src.config import get_settings
from app.src.services.assessment_service import AssessmentService
from app.src.services.job_manager import JobManager
from app.src.services.llm_service import LLMService
from app.src.search_modules.modules import ALL_SEARCH_MODULES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Check your .env file.")

    job_manager = JobManager()
    llm_service = LLMService()
    assessment_service = AssessmentService(
        job_manager=job_manager,
        llm_service=llm_service,
    )

    app.state.job_manager = job_manager
    app.state.assessment_service = assessment_service

    yield


app = FastAPI(
    title="Company Risk Assessment API",
    description="an automated company background check service that searches multiple public data sources and uses an LLM to synthesise findings into a structured risk report",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_API_PREFIX = "/api/v1"
_auth = [Depends(verify_api_key)]
app.include_router(assessment.router, prefix=_API_PREFIX, dependencies=_auth)
app.include_router(jobs.router, prefix=_API_PREFIX, dependencies=_auth)


@app.get("/", tags=["Health"], include_in_schema=False)
async def root():
    return {"service": "Company Risk Assessment API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health", tags=["Health"], summary="Health check")
async def health():
    return {"status": "healthy"}


@app.get("/api/v1/modules", tags=["Modules"], summary="List all registered search modules", dependencies=_auth)
async def list_modules():
    return [
        {
            "module_id": cls.module_id,
            "module_name": cls.module_name,
            "description": cls.description,
            "jurisdictions": cls.jurisdictions if cls.jurisdictions else "all",
        }
        for cls in ALL_SEARCH_MODULES
    ]
