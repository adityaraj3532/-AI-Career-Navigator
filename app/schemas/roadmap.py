from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CreateRoadmapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    career_id: UUID
    hours_per_week: Optional[float] = Field(default=None, ge=1.0, le=80.0)
    timezone: Optional[str] = "Asia/Kolkata"
    start_date: Optional[datetime] = None


class RoadmapItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    roadmap_id: UUID
    phase_id: Optional[UUID] = None
    item_code: Optional[str] = None
    type: str
    title: str
    source_url: Optional[str] = None
    estimated_minutes: int
    difficulty: int
    topic: str
    skill_id: Optional[UUID] = None
    optional: bool = False
    status: str
    scheduled_week: Optional[int] = None
    scheduled_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    order_index: int = 0


class RoadmapPhaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    phase_order: int
    description: Optional[str] = None
    items: List[RoadmapItemResponse] = Field(default_factory=list)


class RoadmapDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    career_id: UUID
    career_title: str
    template_id: UUID
    template_version: int
    title: str
    status: str
    timezone: str
    hours_per_week: float
    start_date: datetime
    target_completion_date: Optional[datetime] = None
    total_weeks: int
    completion_percentage: float
    total_items: int
    completed_items: int
    phases: List[RoadmapPhaseResponse] = Field(default_factory=list)
    backlog_items: List[RoadmapItemResponse] = Field(default_factory=list)
    target_entrances: List[Dict[str, Any]] = Field(default_factory=list)


class UpdateRoadmapItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    force_undo: bool = False


class ReplanRoadmapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replan_date: Optional[datetime] = None
    hours_per_week: Optional[float] = Field(default=None, ge=1.0, le=80.0)


class ReplanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roadmap_id: UUID
    preserved_count: int
    rescheduled_count: int
    total_weeks: int
    summary: Dict[str, Any]
