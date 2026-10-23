from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.career import CareerDetailResponse, CareersListResponse
from app.schemas.compatibility import (
    CompatibilityHistoryResponse,
    CompatibilitySnapshotResponse,
)
from app.services.career_service import CareerService
from app.services.compatibility_service import CompatibilityService

router = APIRouter(prefix="/careers", tags=["Career Catalog"])


@router.get(
    "",
    response_model=CareersListResponse,
    summary="List careers with filtering, pagination, and optional student compatibility scores",
)
async def list_careers(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
    cluster: Optional[str] = Query(None, description="Filter by career cluster"),
    demand: Optional[str] = Query(None, description="Filter by industry demand level (very_high, high, moderate, steady)"),
    min_salary: Optional[int] = Query(None, description="Minimum salary in INR per year"),
    max_salary: Optional[int] = Query(None, description="Maximum salary in INR per year"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(20, ge=1, le=50, description="Items per page (max 50)"),
) -> CareersListResponse:
    service = CareerService(session)
    return await service.list_careers(
        user=current_user,
        cluster=cluster,
        demand=demand,
        min_salary=min_salary,
        max_salary=max_salary,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/search",
    response_model=CareersListResponse,
    summary="Search careers with alias matching and optional student compatibility scores",
)
async def search_careers(
    session: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query(..., min_length=1, max_length=60, description="Search query string"),
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=50, description="Items per page"),
) -> CareersListResponse:
    service = CareerService(session)
    return await service.search_careers(
        query=q,
        user=current_user,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{career_id}/compatibility",
    response_model=CompatibilitySnapshotResponse,
    summary="Get or generate transparent compatibility score and factor breakdown for a career",
)
async def get_career_compatibility(
    career_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CompatibilitySnapshotResponse:
    service = CompatibilityService(session)
    return await service.get_compatibility(user=current_user, career_id=career_id)


@router.get(
    "/{career_id}/compatibility/history",
    response_model=CompatibilityHistoryResponse,
    summary="Get append-only history of compatibility evaluations for this career",
)
async def get_career_compatibility_history(
    career_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CompatibilityHistoryResponse:
    service = CompatibilityService(session)
    return await service.get_compatibility_history(user=current_user, career_id=career_id)


@router.get(
    "/{career_id}",
    response_model=CareerDetailResponse,
    summary="Get full career details with eager-loaded exams, colleges, courses, certificates, internships, and related careers",
)
async def get_career_detail(
    career_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
) -> CareerDetailResponse:
    service = CareerService(session)
    return await service.get_career_detail(career_id=career_id, user=current_user)

