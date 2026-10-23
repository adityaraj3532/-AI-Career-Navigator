from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

ChatMode = Literal["career", "roadmap", "skills", "interview"]
ChatRole = Literal["user", "assistant"]
AIStatus = Literal["ok", "fallback", "safety"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: Optional[UUID] = None
    mode: Optional[ChatMode] = None
    career_id: Optional[UUID] = None
    message: str = Field(..., min_length=1, max_length=1000)
    client_message_id: Optional[str] = Field(None, min_length=1, max_length=64)


class ChatSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    type: str
    title: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    conversation_id: UUID
    seq: int
    role: str
    content: str
    sources: List[ChatSource]
    ai_status: str
    created_at: datetime


class ConversationSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    mode: str
    career_id: Optional[UUID]
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    mode: str
    career_id: Optional[UUID]
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse]


# LLM Gateway Output Schema
class AIChatOutput(BaseModel):
    answer: str
    used_record_ids: List[str] = Field(default_factory=list)
    in_scope: bool = True
