from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, max_length=128)
    budget_level: Optional[str] = Field(None, description="'low', 'medium', or 'high'")
    hours_available_per_week: Optional[int] = Field(None, ge=0, le=168)
    subjects_of_interest: Optional[List[str]] = Field(None, max_length=20)
    skills: Optional[List[Dict[str, Any]]] = Field(None, max_length=50)


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    name: Optional[str] = None
    budget_level: Optional[str] = None
    hours_available_per_week: Optional[int] = None
    subjects_of_interest: List[str]
    skills: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
