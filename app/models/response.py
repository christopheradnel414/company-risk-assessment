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
    data: Optional[Any] = Field(None, description="Structured data extracted by the LLM from raw source data")
    error: Optional[str] = Field(None, description="Error message if the module failed")


# ── Risk summary produced by the LLM synthesis step ──────────────────────────

class RiskSummary(BaseModel):
    overall_risk_level: Literal["high", "medium", "low", "unknown"] = Field(
        description="Aggregated risk level across all search findings"
    )
    risk_score: int = Field(
        ge=0, le=100,
        description="Numeric risk score: 0 = no risk, 100 = maximum risk",
    )
    key_findings: List[str] = Field(description="Most significant findings across all modules")
    red_flags: List[str] = Field(description="Specific concerning indicators identified")
    positive_indicators: List[str] = Field(description="Factors that reduce risk or indicate legitimacy")
    recommendation: Literal["proceed", "caution", "avoid", "insufficient_data"] = Field(
        description="Recommended action based on findings"
    )


# ── Final assessment result ───────────────────────────────────────────────────

class AssessmentResult(BaseModel):
    company_name: Optional[str]
    registration_number: Optional[str]
    jurisdiction: str
    search_results: List[SearchResult]
    risk_summary: RiskSummary
    search_conclusion: str = Field(description="Narrative summary of all findings and risk assessment")


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
