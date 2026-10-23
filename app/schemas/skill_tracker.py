from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeclareSkillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: Optional[UUID] = None
    skill_slug: Optional[str] = Field(None, min_length=2, max_length=64)
    level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")

    @model_validator(mode="after")
    def validate_identifier(self) -> "DeclareSkillRequest":
        if not self.skill_id and not self.skill_slug:
            raise ValueError("Either skill_id or skill_slug must be provided")
        return self


class UserSkillItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: UUID
    skill_slug: str
    skill_name: str
    category: str
    current_level: str
    confidence: str
    updated_at: datetime


class UserSkillsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: List[UserSkillItemResponse]
    total_count: int


class RecommendedItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    type: str  # e.g., "roadmap_step", "course", "practice"
    description: Optional[str] = None
    target_subtopic: Optional[str] = None


class SkillReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: UUID
    skill_slug: str
    skill_name: str
    current_level: str
    confidence: str
    strengths: List[str]
    weak_subtopics: List[str]
    trend_over_time: Optional[Dict[str, Any]] = None  # None if < 2 evidence items
    recommended_next_items: List[RecommendedItemResponse]
    report_status: str = "fallback"
    report_text: str
    evidence_count: int
