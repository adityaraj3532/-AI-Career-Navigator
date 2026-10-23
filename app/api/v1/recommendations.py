from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationActionRequest,
    RecommendationActionResponse,
    RecommendationListResponse,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations & Opportunities"])


@router.get(
    "",
    response_model=RecommendationListResponse,
    summary="Get curated recommendations for internships, degrees, certificates, and free resources",
)
async def get_recommendations(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    career_id: Optional[UUID] = Query(None, description="Filter recommendations for specific career"),
    budget: Optional[str] = Query(None, description="Budget level ('low', 'medium', 'high')"),
    location: Optional[str] = Query(None, description="Preferred location or 'Remote'"),
    max_hours: Optional[int] = Query(None, description="Maximum available hours per week"),
    type: Optional[str] = Query(None, pattern="^(internship|course|certificate|resource)$", description="Filter by opportunity type"),
    include_dismissed: bool = Query(False, description="Include dismissed items in results"),
    saved_only: bool = Query(False, description="Return only saved items"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=50, description="Items per page (max 50)"),
) -> RecommendationListResponse:
    service = RecommendationService(session)
    return await service.get_recommendations(
        user=current_user,
        career_id=career_id,
        budget_level=budget,
        location=location,
        max_hours=max_hours,
        item_type=type,
        include_dismissed=include_dismissed,
        saved_only=saved_only,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{item_type}/{item_id}/action",
    response_model=RecommendationActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Save, dismiss, restore, or mark a recommended opportunity as done",
)
async def interact_with_recommendation(
    item_type: Annotated[str, Path(pattern="^(internship|course|certificate|resource)$")],
    item_id: UUID,
    req: RecommendationActionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationActionResponse:
    service = RecommendationService(session)
    return await service.interact_with_recommendation(
        user=current_user,
        item_type=item_type,
        item_id=item_id,
        new_state=req.state,
    )
