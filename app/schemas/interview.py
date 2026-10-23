from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class KeyPointItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=64, description="Unique identifier for key point, e.g. kp_1")
    text: str = Field(..., min_length=3, max_length=500, description="Criteria description")
    weight: float = Field(..., gt=0.0, le=1.0, description="Weight proportion between 0.0 and 1.0")
    keywords: List[str] = Field(default_factory=list, description="Keywords and phrases for fallback matching")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Key point id cannot be empty.")
        return clean


class DimensionScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage_score: int = Field(..., ge=0, le=100)
    depth_score: int = Field(..., ge=0, le=100)
    structure_score: int = Field(..., ge=0, le=100)
    overall_score: int = Field(..., ge=0, le=100)
    covered_points: List[str] = Field(default_factory=list)
    rubric_version: str = Field(default="v1.0.0")


class ScoringResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rubric_version: str
    scores: DimensionScores
    covered_points: List[str]
    scoring_method: Literal["ai", "fallback"]
    confidence: Literal["high", "medium", "low"]
    details: Dict[str, Any] = Field(default_factory=dict)


class InterviewQuestionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_id: Optional[UUID] = None
    type: Literal["technical", "hr"]
    level: Literal["beginner", "intermediate", "advanced"]
    text: str = Field(..., min_length=10, max_length=2000)
    key_points: List[KeyPointItem] = Field(..., min_length=1, max_length=10)
    sample_answer: Optional[str] = Field(None, max_length=4000)
    source_note: Optional[str] = Field(None, max_length=500)

    @field_validator("key_points")
    @classmethod
    def validate_weights(cls, points: List[KeyPointItem]) -> List[KeyPointItem]:
        total = sum(p.weight for p in points)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Key point weights must sum to 1.0 (got {total:.4f}).")
        return points


class InterviewQuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    career_id: Optional[UUID] = None
    type: str
    level: str
    text: str
    key_points: List[KeyPointItem]
    sample_answer: Optional[str] = None
    status: str
    source_note: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    created_at: datetime
