from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.compatibility import (
    ShortlistActionResponse,
    ShortlistListResponse,
)
from app.services.compatibility_service import CompatibilityService

router = APIRouter(prefix="/shortlist", tags=["Career Shortlist"])


@router.get(
    "",
    response_model=ShortlistListResponse,
    summary="List all shortlisted careers for the authenticated user",
)
async def get_shortlist(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ShortlistListResponse:
    service = CompatibilityService(session)
    return await service.get_user_shortlist(current_user)


@router.post(
    "/{career_id}",
    response_model=ShortlistActionResponse,
    summary="Add a verified career to the user's shortlist (max 20, idempotent)",
)
async def add_to_shortlist(
    career_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ShortlistActionResponse:
    service = CompatibilityService(session)
    return await service.add_to_shortlist(current_user, career_id)


@router.delete(
    "/{career_id}",
    response_model=ShortlistActionResponse,
    summary="Remove a career from the user's shortlist (idempotent)",
)
async def remove_from_shortlist(
    career_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ShortlistActionResponse:
    service = CompatibilityService(session)
    return await service.remove_from_shortlist(current_user, career_id)
