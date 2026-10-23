from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.portfolio import PortfolioResponse
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
