from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RecommendationItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    item_type: str = Field(..., pattern="^(internship|course|certificate|resource)$")
    title: str
    provider: Optional[str] = None
    cost_inr: Optional[int] = None
    is_free: bool = False
    duration: Optional[str] = None
    mode: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    application_deadline: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    why_it_fits: str
    user_state: str = "none"  # "none" | "saved" | "dismissed" | "done"
    match_score: int


class RecommendationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[RecommendationItemSchema]
    total_count: int
    page: int
    page_size: int
    personalised: bool


class RecommendationActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str = Field(..., pattern="^(saved|dismissed|done|none)$")


class RecommendationActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: str
    item_id: UUID
    state: str
    updated_at: datetime
