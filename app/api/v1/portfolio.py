from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.models.user import User
from app.schemas.portfolio import (
    GeneratePortfolioTextRequest,
    GeneratePortfolioTextResponse,
    OwnerPortfolioResponse,
    PortfolioResponse,
    PortfolioSummaryRequest,
    PortfolioSummaryResponse,
    PublicPortfolioViewResponse,
    ResumeExportResponse,
    UpdatePortfolioRequest,
)
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def get_portfolio_service(
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> PortfolioService:
    return PortfolioService(db, gateway=gateway)


@router.get(
    "",
    response_model=OwnerPortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Get owner portfolio",
    description="Private owner view of the portfolio. GET MUST NOT write. If no customized record exists, returns computed draft suggestions with is_persisted=False.",
)
async def get_owner_portfolio(
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> OwnerPortfolioResponse:
    return await service.get_owner_portfolio(current_user)


@router.put(
    "",
    response_model=OwnerPortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update owner portfolio",
    description="Updates custom sections, slug, public visibility, and visibility allowlist for sections. Creates the database record on first PUT.",
)
async def update_owner_portfolio(
    req: UpdatePortfolioRequest,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> OwnerPortfolioResponse:
    return await service.update_owner_portfolio(current_user, req)


@router.post(
    "/generate-text",
    response_model=GeneratePortfolioTextResponse,
    status_code=status.HTTP_200_OK,
    summary="AI assistant for portfolio text",
    description="Generates an about section or project description strictly synthesized from user facts without hallucinating achievements.",
)
async def generate_portfolio_text(
    req: GeneratePortfolioTextRequest,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> GeneratePortfolioTextResponse:
    return await service.generate_portfolio_text(current_user, req)


@router.get(
    "/p/{slug}",
    response_model=PublicPortfolioViewResponse,
    status_code=status.HTTP_200_OK,
    summary="Public shareable portfolio page by slug",
    description="Public vanity view by custom or random slug. Returns 404 if missing, private, or disabled. Filtered by section visibility.",
)
async def get_public_portfolio_by_slug(
    slug: str,
    request: Request,
    response: Response,
    service: PortfolioService = Depends(get_portfolio_service),
) -> PublicPortfolioViewResponse:
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"pub_slug:{client_ip}", max_requests=60, window_seconds=60)

    # Search engine and caching headers
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return await service.get_public_portfolio_by_slug(slug)


# --- Legacy / Aggregation Endpoints ---
@router.get(
    "/aggregated",
    response_model=PortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated raw portfolio metrics",
    description="Read-only multi-domain raw aggregation across verified skills, recommendations, roadmap milestones, and diagnostic tests.",
)
async def get_raw_aggregated_portfolio(
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioResponse:
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
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioSummaryResponse:
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
    service: PortfolioService = Depends(get_portfolio_service),
) -> ResumeExportResponse:
    return await service.export_resume_markdown(current_user)

