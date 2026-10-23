from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID
import zoneinfo
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_iana_timezone(tz_name: str) -> str:
    """Validate that tz_name is a valid IANA timezone name."""
    if tz_name not in zoneinfo.available_timezones():
        raise ValueError(f"Invalid IANA timezone: '{tz_name}'")
    return tz_name


# ==============================================================================
# MILESTONE RULE PARAMETERS
# ==============================================================================

class EventCountParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: str = Field(..., min_length=1, max_length=64)
    count: int = Field(..., gt=0, le=10000)


class StreakParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: int = Field(..., gt=0, le=3650)


class PhaseCompletedParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase_order: int = Field(..., gt=0, le=100)


MilestoneParamsType = Union[EventCountParams, StreakParams, PhaseCompletedParams]


class MilestoneRuleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    key: str
    rule_type: Literal["event_count_at_least", "streak_at_least", "phase_completed"]
    params: Dict[str, Any]
    title: str
    version: int
    active: bool


class UserMilestoneResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    rule_key: str
    title: str
    rule_type: str
    badge_type: Literal["effort", "verified_achievement"]
    awarded_at: datetime
    evidence: Dict[str, Any]


# ==============================================================================
# WEEKLY GOALS
# ==============================================================================

class WeeklyGoalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    week_start: date
    goal_type: Literal["roadmap_items", "minutes"]
    target: int = Field(..., gt=0)

    @field_validator("week_start")
    @classmethod
    def validate_monday(cls, v: date) -> date:
        if v.weekday() != 0:
            raise ValueError(f"week_start must be a Monday, got {v.strftime('%A')} ({v})")
        return v

    @model_validator(mode="after")
    def validate_target_bounds(self) -> "WeeklyGoalRequest":
        if self.goal_type == "minutes":
            # Maximum minutes in a full week = 7 * 24 * 60 = 10,080 minutes
            if self.target > 10080:
                raise ValueError("Weekly minute target cannot exceed available hours in a week (10,080 minutes)")
        elif self.goal_type == "roadmap_items":
            if self.target > 500:
                raise ValueError("Weekly roadmap item target cannot exceed 500 items")
        return self


class WeeklyGoalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    week_start: date
    goal_type: str
    target: int
    actual: int
    progress_percent: float
    is_completed: bool


# ==============================================================================
# PROGRESS SUMMARY
# ==============================================================================

class PhaseProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase_id: Optional[UUID]
    phase_order: int
    name: str
    total_items: int
    done_items: int
    percent: float


class SkillGainedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill_name: str
    level: str
    provenance: str  # test_assessed, self_reported, interview


class ProgressSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: str
    roadmap_percent: Optional[float]
    phases: List[PhaseProgress]
    skills_gained: List[SkillGainedItem]
    current_streak: int
    longest_streak: int
    milestones: List[UserMilestoneResponse]
    weekly_goals: List[WeeklyGoalResponse]
    weekly_summary: Optional[str] = None
