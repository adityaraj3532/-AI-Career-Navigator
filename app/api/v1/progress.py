"""API routes for progress tracking, streaks, milestones, and weekly goals."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.progress import (
    ProgressSummaryResponse,
    WeeklyGoalRequest,
    WeeklyGoalResponse,
)
from app.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get(
    "/summary",
    response_model=ProgressSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user progress summary, streaks, milestones, and goals",
)
async def get_progress_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressSummaryResponse:
    """Retrieve full progress summary for the authenticated user.

    Pure read endpoint: creates no database records and never modifies state.
    Returns 404 if user has no student profile.
    """
    service = ProgressService(db)
    return await service.get_progress_summary(current_user)


@router.put(
    "/weekly-goals",
    response_model=WeeklyGoalResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update weekly goal for current or next week",
)
async def upsert_weekly_goal(
    req: WeeklyGoalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WeeklyGoalResponse:
    """Set or update weekly target for roadmap items or minutes.

    Only current week and next week Monday dates are editable.
    Returns 404 if user has no student profile.
    """
    service = ProgressService(db)
    return await service.upsert_weekly_goal(current_user, req)
