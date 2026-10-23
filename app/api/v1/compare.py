from typing import Annotated, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.compatibility import CompareRequest, CompareResponse
from app.services.compatibility_service import CompatibilityService

router = APIRouter(prefix="/compare", tags=["Career Comparison"])


@router.post(
    "",
    response_model=CompareResponse,
    summary="Compare 2-4 verified careers across interest fit, skills, budget, difficulty, and salaries",
)
async def compare_careers(
    req: CompareRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
) -> CompareResponse:
    service = CompatibilityService(session)
    return await service.compare_careers(current_user, req.career_ids)
