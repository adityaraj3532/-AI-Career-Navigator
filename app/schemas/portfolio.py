from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PortfolioProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    name: Optional[str] = None
    email: str
    education_level: Optional[str] = None
    target_career: Optional[str] = None
    subjects_of_interest: List[str] = Field(default_factory=list)


class PortfolioSkillItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: UUID
    slug: str
    name: str
    current_level: str
    confidence: str
    evidence_count: int = 0
    updated_at: datetime


class PortfolioCompletedRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: UUID
    item_type: str
    title: str
    provider: Optional[str] = None
    source_url: Optional[str] = None
    completed_at: datetime


class PortfolioCompletedMilestone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: UUID
    roadmap_id: UUID
    type: str
    title: str
    topic: str
    difficulty: int
    source_url: Optional[str] = None
    completed_at: Optional[datetime] = None


class PortfolioDiagnosticTest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: UUID
    type: str
    topic: str
    demonstrated_level: Optional[str] = None
    confidence: Optional[str] = None
    score_percentage: Optional[int] = None
    completed_at: Optional[datetime] = None


class PortfolioSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_skills_tracked: int
    total_recommendations_completed: int
    total_milestones_completed: int
    total_tests_completed: int


class PortfolioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: PortfolioProfile
    summary: PortfolioSummary
    skills: List[PortfolioSkillItem]
    completed_recommendations: List[PortfolioCompletedRecommendation]
    completed_milestones: List[PortfolioCompletedMilestone]
    diagnostic_tests: List[PortfolioDiagnosticTest]


class PublicPortfolioProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    education_level: Optional[str] = None
    target_career: Optional[str] = None
    subjects_of_interest: List[str] = Field(default_factory=list)


class PublicPortfolioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: PublicPortfolioProfile
    summary: PortfolioSummary
    skills: List[PortfolioSkillItem]
    completed_recommendations: List[PortfolioCompletedRecommendation]
    completed_milestones: List[PortfolioCompletedMilestone]
    diagnostic_tests: List[PortfolioDiagnosticTest]


class PortfolioSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: Optional[str] = Field(None, max_length=120)


class PortfolioSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elevator_pitch: str
    key_highlights: List[str]
    suggested_tagline: str


class ResumeExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown_resume: str
    export_format: str = "markdown"
    generated_at: datetime
