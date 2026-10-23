from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.adaptive_test import (
    FinishTestRequest,
    FinishTestResponse,
    LanguageAdvisorRequest,
    LanguageAdvisorResponse,
    StartTestRequest,
    StartTestResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    TestHistoryResponse,
)
from app.services.adaptive_test_service import AdaptiveTestService

router = APIRouter(prefix="/tests", tags=["Adaptive Diagnostic Tests"])


@router.get(
    "/history",
    response_model=TestHistoryResponse,
    summary="Get paginated history of past adaptive test attempts for the current user",
)
async def get_test_history(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
) -> TestHistoryResponse:
    service = AdaptiveTestService(session)
    return await service.get_test_history(current_user, page=page, page_size=page_size)


@router.post(
    "/language-advisor",
    response_model=LanguageAdvisorResponse,
    summary="Deterministic programming language recommendation questionnaire with AI-guided explanation",
)
async def get_language_advice(
    req: LanguageAdvisorRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LanguageAdvisorResponse:
    service = AdaptiveTestService(session)
    return await service.get_language_advice(current_user, req)


@router.post(
    "/start",
    response_model=StartTestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an adaptive diagnostic skill assessment or aptitude test for a career",
)
async def start_test(
    req: StartTestRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StartTestResponse:
    service = AdaptiveTestService(session)
    return await service.start_test(current_user, req)


@router.post(
    "/{test_id}/answer",
    response_model=SubmitAnswerResponse,
    summary="Submit an answer to a question in the adaptive test and receive the next question",
)
async def submit_answer(
    test_id: UUID,
    req: SubmitAnswerRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SubmitAnswerResponse:
    service = AdaptiveTestService(session)
    return await service.submit_answer(current_user, test_id, req)


@router.post(
    "/{test_id}/finish",
    response_model=FinishTestResponse,
    summary="Complete test and compute demonstrated proficiency level, confidence, and score",
)
async def finish_test(
    test_id: UUID,
    req: FinishTestRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FinishTestResponse:
    service = AdaptiveTestService(session)
    return await service.finish_test(current_user, test_id)
