from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskType = Literal["roadmap_item", "user_custom", "ai_suggestion"]
TaskPriority = Literal["low", "medium", "high"]
TaskStatus = Literal["pending", "in_progress", "completed", "cancelled"]


class PlannerTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    scheduled_date: date
    estimated_minutes: int = Field(..., gt=0, le=1440)
    task_type: TaskType = "user_custom"
    roadmap_item_id: Optional[UUID] = None
    priority: TaskPriority = "medium"
    notes: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_roadmap_item_link(self) -> "PlannerTaskCreate":
        if self.task_type == "roadmap_item" and self.roadmap_item_id is None:
            raise ValueError("roadmap_item_id is required when task_type is 'roadmap_item'.")
        if self.task_type != "roadmap_item" and self.roadmap_item_id is not None:
            raise ValueError("roadmap_item_id must be None when task_type is not 'roadmap_item'.")
        return self


class PlannerTaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[TaskStatus] = None
    scheduled_date: Optional[date] = None
    estimated_minutes: Optional[int] = Field(None, gt=0, le=1440)
    priority: Optional[TaskPriority] = None
    notes: Optional[str] = Field(None, max_length=1000)


class PlannerTaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    roadmap_item_id: Optional[UUID]
    task_type: str
    title: str
    notes: Optional[str]
    estimated_minutes: int
    scheduled_date: date
    status: str
    priority: str
    user_rescheduled: bool
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    suggested: bool = False


class PlannerDayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    timezone: str
    available_minutes: Optional[int]
    planned_minutes: int
    is_overallocated: Optional[bool]
    tasks: List[PlannerTaskResponse]
    suggestions: List[PlannerTaskResponse]
    weekly_overview: Dict[str, Any]
