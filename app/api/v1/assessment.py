from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.assessment import (
    AttemptResponse,
    QuestionsListResponse,
    SaveAnswersRequest,
)
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessment", tags=["Career Assessment"])


@router.get(
    "/questions",
    response_model=QuestionsListResponse,
    summary="Retrieve active assessment questions and Likert scale descriptions",
)
async def get_questions(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionsListResponse:
    service = AssessmentService(session)
    return await service.get_active_questions()


@router.get(
    "/attempt",
    response_model=AttemptResponse,
    summary="Resume or initialize the current user's active draft assessment attempt",
)
async def get_current_attempt(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AttemptResponse:
    service = AssessmentService(session)
    return await service.get_or_create_draft_attempt(current_user.id)


@router.post(
    "/answers",
    response_model=AttemptResponse,
    summary="Save draft answers and track progress for active assessment",
)
async def save_answers_post(
    req: SaveAnswersRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AttemptResponse:
    service = AssessmentService(session)
    return await service.save_answers(current_user.id, req)


@router.put(
    "/answers",
    response_model=AttemptResponse,
    summary="Upsert draft answers (PUT alias) for active assessment",
)
async def save_answers_put(
    req: SaveAnswersRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AttemptResponse:
    service = AssessmentService(session)
    return await service.save_answers(current_user.id, req)


@router.get(
    "/attempts/{attempt_id}",
    response_model=AttemptResponse,
    summary="Get specific attempt by ID (enforcing strict ownership)",
)
async def get_attempt_by_id(
    attempt_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AttemptResponse:
    service = AssessmentService(session)
    attempt = await service.repo.get_attempt_by_id(attempt_id, current_user.id)
    if not attempt:
        from app.core.exceptions import AppException
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ATTEMPT_NOT_FOUND",
            message="Assessment attempt not found or unauthorized.",
        )
    return service._format_attempt_response(attempt)
