from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class StartInterviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_id: Optional[UUID] = None
    type: Literal["technical", "hr"]
    level: Literal["beginner", "intermediate", "advanced"]
    num_questions: int = Field(default=3, ge=1, le=5)

    @model_validator(mode="after")
    def validate_career_for_technical(self) -> "StartInterviewRequest":
        if self.type == "technical" and not self.career_id:
            raise ValueError("career_id is required for technical mock interviews.")
        return self


class PublicSessionQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    order: int
    question_text: str
    is_follow_up: bool = False


class StartInterviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    career_id: Optional[UUID] = None
    type: str
    level: str
    status: str
    expires_at: datetime
    current_question: PublicSessionQuestion
    total_questions: int


class SubmitAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_question_id: UUID
    answer_text: str = Field(..., min_length=1, max_length=2000)


class QuestionFeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_question_id: UUID
    scores: DimensionScores
    covered_points: List[str]
    scoring_method: Literal["ai", "fallback"]
    confidence: Literal["high", "medium", "low"]
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    sample_answer: Optional[str] = None
    next_question: Optional[PublicSessionQuestion] = None
    session_completed: bool
    practice_guidance_note: str = Field(default="Feedback is practice guidance to support interview preparation.")


class TranscriptItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_question_id: UUID
    order: int
    question_text: str
    is_follow_up: bool
    answer_text: Optional[str] = None
    submitted_at: Optional[datetime] = None
    scores: Optional[DimensionScores] = None
    covered_points: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    sample_answer: Optional[str] = None


class SessionDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    career_id: Optional[UUID] = None
    type: str
    level: str
    status: str
    started_at: datetime
    expires_at: datetime
    completed_at: Optional[datetime] = None
    overall_score: Optional[int] = None
    coverage_score: Optional[int] = None
    depth_score: Optional[int] = None
    structure_score: Optional[int] = None
    questions: List[TranscriptItem]
    practice_guidance_note: str = Field(default="Feedback is practice guidance to support interview preparation.")


class InterviewHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    career_id: Optional[UUID] = None
    type: str
    level: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    overall_score: Optional[int] = None
    coverage_score: Optional[int] = None
    depth_score: Optional[int] = None
    structure_score: Optional[int] = None


class InterviewHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[InterviewHistoryItem]
    total: int
    page: int
    page_size: int


class DimensionTrend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str
    average_score: float
    change_pct: float
    progression: List[int]


class InterviewAnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_sufficient_data: bool
    total_completed: int
    message: Optional[str] = None
    trends: Optional[Dict[str, DimensionTrend]] = None
    weakest_dimension: Optional[str] = None
    strongest_dimension: Optional[str] = None
