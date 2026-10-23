from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class QuestionOptionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str


class QuestionPublicSchema(BaseModel):
    """
    Public question view served during test execution.
    CRITICAL: Never includes correct_option_id or explanation.
    """
    model_config = ConfigDict(extra="forbid")

    id: UUID
    difficulty: int = Field(..., ge=1, le=3)
    question_text: str
    options: List[QuestionOptionSchema]


class StartTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_id: UUID
    type: str = Field(..., pattern="^(skill|aptitude)$", description="'skill' or 'aptitude'")
    topic: str = Field(..., min_length=2, max_length=64)
    language: Optional[str] = Field(None, max_length=32, description="Language selection (e.g. 'python', 'cpp', 'java')")


class StartTestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: UUID
    career_id: UUID
    type: str
    topic: str
    language: Optional[str] = None
    status: str
    time_limit_seconds: int
    total_questions: int
    current_question_index: int
    current_question: QuestionPublicSchema


class SubmitAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    selected_option_id: str = Field(..., min_length=1, max_length=32)
    time_taken_seconds: Optional[int] = Field(None, ge=0, le=3600)


class SubmitAnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_correct: bool
    explanation: str
    next_difficulty: int
    current_question_index: int
    total_questions: int
    can_finish: bool
    next_question: Optional[QuestionPublicSchema] = None


class FinishTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinishTestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: UUID
    status: str
    score_percentage: int
    total_correct: int
    total_questions: int
    demonstrated_level: str
    confidence: str
    recommendations: List[str]
    disclaimer_note: str
    finished_at: datetime


class TestHistoryItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    career_id: UUID
    type: str
    topic: str
    language: Optional[str] = None
    status: str
    demonstrated_level: Optional[str] = None
    confidence: Optional[str] = None
    score_percentage: Optional[int] = None
    total_correct: Optional[int] = None
    total_answered: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class TestHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[TestHistoryItemSchema]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class LanguageAdvisorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_goal: str = Field(..., description="e.g. 'dsa_interviews', 'backend_development', 'machine_learning', 'embedded_systems'")
    prior_experience: Optional[str] = Field("beginner", description="'beginner', 'intermediate', 'advanced'")
    target_role: Optional[str] = Field(None, description="e.g. 'Software Engineer', 'Data Scientist'")


class LanguageAdvisorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended_language: str
    language_display_name: str
    why_it_fits: str
    alternative_options: List[str]
    next_steps: List[str]
