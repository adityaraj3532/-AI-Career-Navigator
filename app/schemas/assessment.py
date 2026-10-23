from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class QuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    question_order: int
    text: str
    dimension: str
    scale_min: int = 1
    scale_max: int = 5


class QuestionsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_version_id: UUID
    version_number: int
    title: str
    description: str
    total_questions: int
    questions: List[QuestionResponse]


class AnswerItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    value: int = Field(..., ge=1, le=5, description="Likert response score between 1 and 5")


class SaveAnswersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: List[AnswerItem] = Field(..., min_length=1, max_length=50)


class SavedAnswerDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    question_order: int
    dimension: str
    value: int
    updated_at: datetime


class AttemptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    assessment_version_id: UUID
    version_number: int
    status: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    total_questions: int
    answered_count: int
    answers: List[SavedAnswerDetail]


class SubmitAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: Optional[UUID] = None


class CareerSuggestionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_id: UUID
    code: str
    title: str
    cluster: str
    overview: str
    source_url: str
    similarity_score: float
    reason: str


class AssessmentResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    attempt_id: UUID
    version: int
    dimension_scores: Dict[str, float]
    holland_code: str
    holland_code_label: str
    traits: List[str]
    skills: List[str]
    recommended_streams: Optional[List[str]] = None
    career_suggestions: List[CareerSuggestionItem]
    ai_explanation: str
    disclaimer_note: str
    created_at: datetime


class MissingQuestionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    missing_question_ids: List[UUID]
    missing_count: int
    total_required: int


class AssessmentExplanationAISchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_explanation: str
    career_reasons: Dict[str, str]


class AssessmentQAMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=1000)


class AssessmentQARequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=500)
    conversation_history: List[AssessmentQAMessage] = Field(default_factory=list, max_length=50)


class AssessmentQAResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    referenced_career_ids: List[UUID] = Field(default_factory=list)
    in_scope: bool = True


class ChooseCareerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_id: UUID


class ChooseCareerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    career_id: UUID
    career_title: str
    result_id: UUID
