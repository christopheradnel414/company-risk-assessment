import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import assessment, jobs
from app.config import get_settings
from app.services.assessment_service import AssessmentService
from app.services.job_manager import JobManager
from app.services.llm_service import LLMService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared services on startup and attach them to app.state."""
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
    app.state.llm_service = llm_service
    app.state.assessment_service = assessment_service

    yield


# ── App factory ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Company Risk Assessment API",
    description="""
## Overview

An automated company background check service that searches multiple public data sources
**in parallel** and uses an LLM to synthesise findings into a structured risk report.

---

## Quick Start

### 1 — Submit a job
```
POST /api/v1/assessments
{
  "company_name": "Acme Consulting Ltd",
  "registration_number": "12345678",
  "jurisdiction": "GB"
}
```
Returns `{ "job_id": "...", "status_url": "/api/v1/jobs/..." }` immediately (HTTP 202).

### 2 — Poll for progress
```
GET /api/v1/jobs/{job_id}
```
The `progress` array shows per-module status in real time.
Results are available once `status` is `"completed"`.

---

## Search Modules

| Module | Coverage | Data Source |
|--------|----------|-------------|
| **Companies House** | 🇬🇧 GB only | api.company-information.service.gov.uk |
| **OpenCorporates** | 🌍 Global | api.opencorporates.com |
| **News & Media** | 🌍 Global | DuckDuckGo News |
| **Adverse Media** | 🌍 Global | DuckDuckGo Web (scam/fraud/complaint queries) |
| **ICIJ Offshore Leaks** | 🌍 Global | offshoreleaks.icij.org |
| **OpenSanctions** | 🌍 Global | api.opensanctions.org |

---

## Extending with New Modules

1. Create a new file in `app/search_modules/`
2. Subclass `BaseSearchModule` and implement `fetch()`
3. Set `jurisdictions = None` (global) or `["GB", "US"]` (specific)
4. Add the class to `ALL_MODULE_CLASSES` in `app/search_modules/registry.py`
""",
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
app.include_router(assessment.router, prefix=_API_PREFIX)
app.include_router(jobs.router, prefix=_API_PREFIX)


# ── Utility endpoints ──────────────────────────────────────────────────────────

@app.get("/", tags=["Health"], include_in_schema=False)
async def root():
    return {"service": "Company Risk Assessment API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health", tags=["Health"], summary="Health check")
async def health():
    """Returns 200 OK when the service is up."""
    return {"status": "healthy"}


@app.get("/api/v1/modules", tags=["Modules"], summary="List all registered search modules")
async def list_modules():
    """
    Returns metadata for every registered search module including
    which jurisdictions each module applies to.
    """
    from app.search_modules.registry import ALL_MODULE_CLASSES

    return [
        {
            "module_id": cls.module_id,
            "module_name": cls.module_name,
            "description": cls.description,
            "jurisdictions": cls.jurisdictions if cls.jurisdictions else "all",
        }
        for cls in ALL_MODULE_CLASSES
    ]
