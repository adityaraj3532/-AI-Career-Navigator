from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.roadmap import (
    CreateRoadmapRequest,
    ReplanResponse,
    ReplanRoadmapRequest,
    RoadmapDetailResponse,
    RoadmapItemResponse,
    UpdateRoadmapItemRequest,
)
from app.services.roadmap_service import RoadmapService

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


@router.post(
    "",
    response_model=RoadmapDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create personalized career roadmap",
)
async def create_roadmap(
    req: CreateRoadmapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoadmapDetailResponse:
    service = RoadmapService(db)
    return await service.create_roadmap(current_user, req)


@router.get(
    "/{id}",
    response_model=RoadmapDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get roadmap details and progress",
)
async def get_roadmap(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoadmapDetailResponse:
    service = RoadmapService(db)
    return await service.get_roadmap(current_user, id)


@router.patch(
    "/items/{id}",
    response_model=RoadmapItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Update roadmap item progress status",
)
async def update_roadmap_item(
    id: UUID,
    req: UpdateRoadmapItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoadmapItemResponse:
    service = RoadmapService(db)
    return await service.update_roadmap_item(current_user, id, req)


@router.post(
    "/{id}/replan",
    response_model=ReplanResponse,
    status_code=status.HTTP_200_OK,
    summary="Replan roadmap pacing and schedule",
)
async def replan_roadmap(
    id: UUID,
    req: ReplanRoadmapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReplanResponse:
    service = RoadmapService(db)
    return await service.replan_roadmap(current_user, id, req)
