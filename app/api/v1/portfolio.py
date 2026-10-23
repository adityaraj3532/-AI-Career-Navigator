from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioResponse,
    PortfolioSummaryRequest,
    PortfolioSummaryResponse,
    PublicPortfolioResponse,
    ResumeExportResponse,
)
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get(
    "",
    response_model=PortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user portfolio",
    description="Read-only aggregated portfolio of the authenticated student, including verified skills, completed recommendations, roadmap milestones, and diagnostic tests.",
)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    service = PortfolioService(db)
    return await service.get_portfolio_for_user(current_user)


@router.post(
    "/summary",
    response_model=PortfolioSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI elevator pitch",
    description="Synthesize verified portfolio skills and roadmap accomplishments into an engaging recruiter-ready elevator pitch.",
)
async def generate_portfolio_summary(
    req: PortfolioSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioSummaryResponse:
    service = PortfolioService(db)
    return await service.generate_portfolio_pitch(current_user, req)


@router.get(
    "/export/resume",
    response_model=ResumeExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export resume in markdown format",
    description="Export a structured markdown resume highlighting tested skills, milestones, and credentials.",
)
async def export_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeExportResponse:
    service = PortfolioService(db)
    return await service.export_resume_markdown(current_user)


@router.get(
    "/public/{user_id}",
    response_model=PublicPortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Public shareable portfolio page",
    description="Shareable, read-only view of a student's verified portfolio without exposing email or private credentials.",
)
async def get_public_portfolio(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PublicPortfolioResponse:
    service = PortfolioService(db)
    return await service.get_public_portfolio(user_id)
