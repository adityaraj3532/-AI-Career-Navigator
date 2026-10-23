from datetime import datetime
from typing import List, Optional
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
