from datetime import datetime
from enum import Enum
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class ModuleStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AMBIGUOUS = "ambiguous"
    COMPLETED = "completed"
    FAILED = "failed"


class CandidateCompany(BaseModel):
    """A company match returned during registry disambiguation."""
    company_name: str
    registration_number: str
    jurisdiction: str
    company_status: Optional[str] = Field(None, description="e.g. active, dissolved")
    source: str = Field(description="Registry that returned this match")
    warnings: List[str]


# ── Per-module progress (returned in job status) ───────────────────────────────

class SearchModuleProgress(BaseModel):
    module_id: str = Field(description="Unique identifier for the search module")
    module_name: str = Field(description="Human-readable module name")
    status: ModuleStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = Field(None, description="Error message if status is 'failed'")


# ── Per-module result (included in final assessment) ──────────────────────────

class SearchResult(BaseModel):
    module_id: str
    module_name: str
    status: ModuleStatus
    data: Optional[Any] = Field(None, description="Structured data from the module (LLM-parsed or direct)")
    error: Optional[str] = Field(None, description="Error message if the module failed")
    schema_errors: Optional[List[str]] = Field(
        None,
        description="Output schema validation errors, if any. Module still completes successfully.",
    )


# ── Risk summary produced by the LLM synthesis step ──────────────────────────

class RiskSummary(BaseModel):
    overall_risk_level: Literal["high", "medium", "low", "unknown"] = Field(
        description="Aggregated risk level derived from risk_score: 0-29=low, 30-59=medium, 60-100=high"
    )
    risk_score: int = Field(description="Numeric risk score 0 (no risk) to 100 (maximum risk)")
    summary: str = Field(description="2-3 sentence narrative conclusion of the overall risk assessment")


# ── Final assessment result ───────────────────────────────────────────────────

class AssessmentResult(BaseModel):
    company_name: Optional[str]
    registration_number: Optional[str]
    jurisdiction: str
    search_results: List[SearchResult]
    risk_summary: RiskSummary
    warnings: List[str]


# ── Job API responses ─────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    progress: List[SearchModuleProgress] = Field(
        description="Status of each individual search module"
    )
    candidates: Optional[List[CandidateCompany]] = Field(
        None,
        description="Ambiguous registry matches — populated when status is 'ambiguous'. "
                    "Resubmit with registration_number to disambiguate.",
    )
    result: Optional[AssessmentResult] = Field(
        None, description="Final assessment result — populated once status is 'completed'"
    )
    error: Optional[str] = Field(
        None, description="Error message — populated when status is 'failed'"
    )


class CreateAssessmentResponse(BaseModel):
    job_id: str
    message: str = "Assessment job created and queued successfully"
    status_url: str = Field(description="URL to poll for job status and results")
