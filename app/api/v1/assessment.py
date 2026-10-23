from typing import Annotated, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import AppException
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.models.user import User
from app.schemas.assessment import (
    AssessmentQARequest,
    AssessmentQAResponse,
    AssessmentResultResponse,
    AttemptResponse,
    ChooseCareerRequest,
    ChooseCareerResponse,
    QuestionsListResponse,
    SaveAnswersRequest,
    SubmitAssessmentRequest,
)
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessment", tags=["Career Assessment"])


def get_assessment_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    gateway: Annotated[LLMGateway, Depends(get_llm_gateway)],
) -> AssessmentService:
    return AssessmentService(session, gateway=gateway)


@router.get(
    "/questions",
    response_model=QuestionsListResponse,
    summary="Retrieve active assessment questions and Likert scale descriptions",
)
async def get_questions(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> QuestionsListResponse:
    return await service.get_active_questions()


@router.get(
    "/attempt",
    response_model=AttemptResponse,
    summary="Resume or initialize the current user's active draft assessment attempt",
)
async def get_current_attempt(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AttemptResponse:
    return await service.get_or_create_draft_attempt(current_user.id)


@router.post(
    "/answers",
    response_model=AttemptResponse,
    summary="Save draft answers and track progress for active assessment",
)
async def save_answers_post(
    req: SaveAnswersRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AttemptResponse:
    return await service.save_answers(current_user.id, req)


@router.put(
    "/answers",
    response_model=AttemptResponse,
    summary="Upsert draft answers (PUT alias) for active assessment",
)
async def save_answers_put(
    req: SaveAnswersRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AttemptResponse:
    return await service.save_answers(current_user.id, req)


@router.get(
    "/attempts/{attempt_id}",
    response_model=AttemptResponse,
    summary="Get specific attempt by ID (enforcing strict ownership)",
)
async def get_attempt_by_id(
    attempt_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AttemptResponse:
    attempt = await service.repo.get_attempt_by_id(attempt_id, current_user.id)
    if not attempt:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ATTEMPT_NOT_FOUND",
            message="Assessment attempt not found or unauthorized.",
        )
    return service._format_attempt_response(attempt)


@router.post(
    "/submit",
    response_model=AssessmentResultResponse,
    summary="Submit completed assessment attempt, run scoring and generate recommendations",
)
async def submit_assessment(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    req: Optional[SubmitAssessmentRequest] = None,
) -> AssessmentResultResponse:
    attempt_id = req.attempt_id if req else None
    return await service.submit_assessment(user=current_user, attempt_id=attempt_id)


@router.get(
    "/results/latest",
    response_model=AssessmentResultResponse,
    summary="Retrieve the user's latest assessment result",
)
async def get_latest_result(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AssessmentResultResponse:
    return await service.get_latest_result(current_user.id)


@router.get(
    "/results",
    response_model=List[AssessmentResultResponse],
    summary="Retrieve all historical assessment results for current user",
)
async def get_all_results(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> List[AssessmentResultResponse]:
    return await service.get_all_results(current_user.id)


@router.get(
    "/results/{result_id}",
    response_model=AssessmentResultResponse,
    summary="Retrieve a specific assessment result by ID (enforcing strict ownership)",
)
async def get_result_by_id(
    result_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AssessmentResultResponse:
    return await service.get_result_by_id(result_id, current_user.id)


@router.post(
    "/results/{result_id}/ask",
    response_model=AssessmentQAResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask vocational questions about assessment results and suggested careers",
)
async def ask_assessment_question(
    result_id: UUID,
    req: AssessmentQARequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AssessmentQAResponse:
    return await service.ask_question(current_user, result_id, req)


@router.post(
    "/results/{result_id}/choose",
    response_model=ChooseCareerResponse,
    status_code=status.HTTP_200_OK,
    summary="Choose target career from assessment result",
)
async def choose_career_from_result(
    result_id: UUID,
    req: ChooseCareerRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> ChooseCareerResponse:
    return await service.choose_career(current_user, result_id, req)
