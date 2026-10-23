from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.skill_tracker import (
    DeclareSkillRequest,
    SkillReportResponse,
    UserSkillItemResponse,
    UserSkillsListResponse,
)
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["Skill Tracker"])


@router.get(
    "",
    response_model=UserSkillsListResponse,
    summary="Get current user's tracked skills",
)
async def get_user_skills(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserSkillsListResponse:
    service = SkillService(session)
    return await service.list_user_skills(current_user.id)


@router.post(
    "/declare",
    response_model=UserSkillItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Self-declare proficiency in a skill (lowest evidence weight)",
)
async def declare_skill(
    req: DeclareSkillRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserSkillItemResponse:
    service = SkillService(session)
    return await service.declare_skill(
        user_id=current_user.id,
        level=req.level,
        skill_id=req.skill_id,
        skill_slug=req.skill_slug,
    )


@router.get(
    "/{skill_id}/report",
    response_model=SkillReportResponse,
    summary="Get detailed skill report with level, confidence, strengths, weak areas, and trend",
)
async def get_skill_report(
    skill_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SkillReportResponse:
    service = SkillService(session)
    return await service.get_skill_report(current_user.id, skill_id)
