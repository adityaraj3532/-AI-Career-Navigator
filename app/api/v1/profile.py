from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["Student Profile"])


@router.get(
    "",
    response_model=ProfileResponse,
    summary="Get current student's profile parameters (budget, hours, subjects, skills)",
)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileResponse:
    service = ProfileService(session)
    return await service.get_profile(current_user)


@router.put(
    "",
    response_model=ProfileResponse,
    summary="Update or create student profile parameters",
)
async def update_profile(
    req: ProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileResponse:
    service = ProfileService(session)
    return await service.update_profile(current_user, req)
