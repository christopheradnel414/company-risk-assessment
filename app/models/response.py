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
    COMPLETED = "completed"
    FAILED = "failed"


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
        description="Aggregated risk level across all search findings"
    )
    negative_indicators: List[str] = Field(description="Specific concerning indicators identified")
    positive_indicators: List[str] = Field(description="Factors that reduce risk or indicate legitimacy")


# ── Final assessment result ───────────────────────────────────────────────────

class AssessmentResult(BaseModel):
    company_name: Optional[str]
    registration_number: Optional[str]
    jurisdiction: str
    search_results: List[SearchResult]
    risk_summary: RiskSummary


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
    result: Optional[AssessmentResult] = Field(
        None, description="Final assessment result — populated once status is 'completed'"
    )


class CreateAssessmentResponse(BaseModel):
    job_id: str
    message: str = "Assessment job created and queued successfully"
    status_url: str = Field(description="URL to poll for job status and results")
