from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.career import SalaryRangesSchema


class FactorBreakdownItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor: str
    status: str = Field(..., description="'present' or 'excluded'")
    base_weight: int
    effective_weight: float
    score: Optional[int] = None
    weighted_score: float
    details: str


class CompatibilitySnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    career_id: UUID
    career_title: str
    overall_score: int
    data_completeness: int
    excluded_factors: List[str]
    factor_breakdown: Dict[str, FactorBreakdownItem]
    strengths: List[str]
    gaps: List[str]
    weights_version: int
    inputs_hash: str
    explanation_status: str
    ai_explanation: Optional[str] = None
    created_at: datetime


class CompatibilityHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[CompatibilitySnapshotResponse]
    total_count: int


class ShortlistItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_id: UUID
    career_title: str
    cluster: str
    demand: str
    salary_ranges: Optional[SalaryRangesSchema] = None
    created_at: datetime
    compatibility_score: Optional[int] = None


class ShortlistListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[ShortlistItemResponse]
    total_count: int


class ShortlistActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    message: str
    career_id: UUID


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_ids: List[UUID] = Field(..., min_length=2, max_length=10)


class CompareCareerItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_id: UUID
    career_title: str
    cluster: str
    interest_fit_score: Optional[int] = None
    skills_fit_score: Optional[int] = None
    overall_compatibility_score: Optional[int] = None
    time_to_job_ready_months: Optional[int] = None
    entrance_difficulty: Optional[str] = None
    salary_ranges: Optional[SalaryRangesSchema] = None
    estimated_college_fees: Optional[Dict[str, Any]] = None


class CompareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    careers: List[CompareCareerItem]
    ai_verdict: Optional[str] = None
