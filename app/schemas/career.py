from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SalaryRangeDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: int = Field(..., description="Minimum salary in INR per year")
    max: int = Field(..., description="Maximum salary in INR per year")


class SalaryRangesSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = "INR"
    is_approximate: bool = True
    as_of_year: int = 2026
    source_url: str
    entry: SalaryRangeDetail
    mid: SalaryRangeDetail
    senior: SalaryRangeDetail


class SkillItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    level: str = Field(..., description="Proficiency level: beginner, intermediate, advanced, or expert")


class EducationPathStageSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    stream: Optional[str] = None
    degree: Optional[str] = None
    description: str


class ExamSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    name: str
    description: str
    conducting_body: str
    exam_level: str
    registration_url: Optional[str] = None
    source_url: str
    status: str


class CollegeSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    location: Dict[str, Any]
    official_url: str
    fees: Optional[Dict[str, Any]] = None
    cutoffs: Optional[Dict[str, Any]] = None
    nirf_rank: Optional[Dict[str, Any]] = None
    source_url: str
    status: str


class CourseSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    title: str
    degree_level: str
    duration: str
    description: str
    source_url: str
    status: str


class CertificateSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    name: str
    issuing_organization: str
    description: str
    url: Optional[str] = None
    source_url: str
    status: str


class InternshipSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    title: str
    domain: str
    stipend_range: Optional[Dict[str, Any]] = None
    duration_months: Optional[int] = None
    locations: List[str]
    description: str
    source_url: str
    status: str


class RelatedCareerSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    title: str
    cluster: str
    overview: str
    demand: str


class CareerListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    title: str
    cluster: str
    aliases: List[str]
    overview: str
    demand: str
    salary_ranges: Optional[SalaryRangesSchema] = None
    status: str
    source_url: str
    compatibility_score: Optional[int] = None


class CareersListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[CareerListItem]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class CareerDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    title: str
    cluster: str
    aliases: List[str]
    overview: str
    description: Optional[str] = None
    day_in_life: Optional[str] = None
    demand: str
    salary_ranges: Optional[SalaryRangesSchema] = None
    required_skills: List[SkillItemSchema]
    education_paths: List[EducationPathStageSchema]
    dimension_weights: Dict[str, Any]
    status: str
    source_url: str
    reviewer: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    compatibility_score: Optional[int] = None
    exams: List[ExamSummaryResponse]
    colleges: List[CollegeSummaryResponse]
    courses: List[CourseSummaryResponse]
    certificates: List[CertificateSummaryResponse]
    internships: List[InternshipSummaryResponse]
    related_careers: List[RelatedCareerSummaryResponse]
