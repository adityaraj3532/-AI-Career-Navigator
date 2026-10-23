from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.models.user import User
from app.repositories.interview_repository import InterviewRepository
from app.repositories.skill_repository import SkillRepository
from app.schemas.interview import (
    InterviewAnalyticsResponse,
    InterviewHistoryResponse,
    QuestionFeedbackResponse,
    SessionDetailResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
)
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/interviews", tags=["interviews"])


def get_interview_service(
    session: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> InterviewService:
    repo = InterviewRepository(session)
    skill_repo = SkillRepository(session)
    return InterviewService(repo=repo, skill_repo=skill_repo, gateway=gateway)


@router.post(
    "/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a mock interview session",
    description="Initiates a new technical or HR interview session for a career. Returns the first question without key criteria.",
)
async def start_interview(
    req: StartInterviewRequest,
    current_user: User = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> StartInterviewResponse:
    return await service.start_interview(current_user.id, req)


@router.post(
    "/{id}/answers",
    response_model=QuestionFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit answer for a question",
    description="Submits candidate answer as text (max 2000 chars), executes rubric scoring, and returns feedback with a model sample answer.",
)
async def submit_answer(
    id: UUID,
    req: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> QuestionFeedbackResponse:
    return await service.submit_answer(current_user.id, id, req)


@router.get(
    "/history",
    response_model=InterviewHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's mock interview history",
    description="Returns paginated list of completed interview sessions with dimension score summaries.",
)
async def get_interview_history(
    type: Optional[str] = Query(None, description="Filter by type (technical or hr)"),
    career_id: Optional[UUID] = Query(None, description="Filter by career ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user: User = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> InterviewHistoryResponse:
    return await service.get_history(
        user_id=current_user.id,
        type=type,
        career_id=career_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/analytics",
    response_model=InterviewAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's interview improvement analytics",
    description="Calculates time-series dimension progressions. Returns null trends if fewer than 2 comparable sessions exist.",
)
async def get_interview_analytics(
    type: Optional[str] = Query(None, description="Filter by type (technical or hr)"),
    current_user: User = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> InterviewAnalyticsResponse:
    return await service.get_analytics(user_id=current_user.id, type=type)


@router.get(
    "/{id}",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed interview session transcript",
    description="Returns full session questions, submitted answers, rubric dimension scores, strengths, improvements, and sample answers.",
)
async def get_interview_session(
    id: UUID,
    current_user: User = Depends(get_current_user),
    service: InterviewService = Depends(get_interview_service),
) -> SessionDetailResponse:
    return await service.get_session_detail(current_user.id, id)
