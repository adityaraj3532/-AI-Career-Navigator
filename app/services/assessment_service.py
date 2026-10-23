import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.assessment import AssessmentAttempt, AssessmentVersion
from app.repositories.assessment_repository import AssessmentRepository
from app.schemas.assessment import (
    AttemptResponse,
    QuestionResponse,
    QuestionsListResponse,
    SaveAnswersRequest,
    SavedAnswerDetail,
)

logger = logging.getLogger("app.services.assessment")


class AssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssessmentRepository(session)

    async def get_active_questions(self) -> QuestionsListResponse:
        version = await self.repo.get_active_version()
        if not version:
            raise AppException(
                status_code=503,
                code="NO_ACTIVE_ASSESSMENT_VERSION",
                message="No active career assessment version is currently available.",
            )

        questions = await self.repo.get_questions_for_version(version.id)
        question_responses = [
            QuestionResponse(
                id=q.id,
                question_order=q.question_order,
                text=q.text,
                dimension=q.dimension,
                scale_min=1,
                scale_max=5,
            )
            for q in questions
        ]

        return QuestionsListResponse(
            assessment_version_id=version.id,
            version_number=version.version_number,
            title=version.title,
            description=version.description,
            total_questions=len(question_responses),
            questions=question_responses,
        )

    async def get_or_create_draft_attempt(self, user_id: UUID) -> AttemptResponse:
        attempt = await self.repo.get_active_draft_attempt(user_id)
        if not attempt:
            version = await self.repo.get_active_version()
            if not version:
                raise AppException(
                    status_code=503,
                    code="NO_ACTIVE_ASSESSMENT_VERSION",
                    message="No active assessment version available to start an attempt.",
                )
            attempt = await self.repo.create_attempt(user_id, version.id)
            await self.session.commit()
            # Reload with relationships
            attempt = await self.repo.get_active_draft_attempt(user_id)

        return self._format_attempt_response(attempt)

    async def save_answers(
        self,
        user_id: UUID,
        req: SaveAnswersRequest,
        attempt_id: UUID = None,
    ) -> AttemptResponse:
        # If attempt_id is provided, verify it belongs to user_id
        if attempt_id is not None:
            attempt = await self.repo.get_attempt_by_id(attempt_id, user_id)
            if not attempt:
                raise AppException(
                    status_code=404,
                    code="ATTEMPT_NOT_FOUND",
                    message="Assessment attempt not found or unauthorized.",
                )
        else:
            attempt = await self.repo.get_active_draft_attempt(user_id)
            if not attempt:
                version = await self.repo.get_active_version()
                if not version:
                    raise AppException(
                        status_code=503,
                        code="NO_ACTIVE_ASSESSMENT_VERSION",
                        message="No active assessment version available.",
                    )
                attempt = await self.repo.create_attempt(user_id, version.id)
                await self.session.commit()

        if attempt.status != "draft":
            raise AppException(
                status_code=400,
                code="ATTEMPT_ALREADY_SUBMITTED",
                message="Cannot modify answers on a submitted assessment attempt.",
            )

        # Validate that all question IDs belong to the attempt's assessment version
        valid_questions = await self.repo.get_questions_for_version(attempt.assessment_version_id)
        valid_q_map = {q.id: q for q in valid_questions}

        for item in req.answers:
            if item.question_id not in valid_q_map:
                raise AppException(
                    status_code=400,
                    code="INVALID_QUESTION_ID",
                    message=f"Question ID '{item.question_id}' does not belong to this assessment version.",
                )

        # Upsert answers
        await self.repo.upsert_answers(attempt.id, req.answers)
        await self.session.commit()

        # Reload updated attempt
        updated_attempt = await self.repo.get_attempt_by_id(attempt.id, user_id)
        return self._format_attempt_response(updated_attempt)

    def _format_attempt_response(self, attempt: AssessmentAttempt) -> AttemptResponse:
        version: AssessmentVersion = attempt.assessment_version
        version_number = version.version_number if version else 1
        total_questions = len(version.questions) if version and version.questions else 30

        saved_details: list[SavedAnswerDetail] = []
        if attempt.answers:
            for ans in attempt.answers:
                q = ans.question
                saved_details.append(
                    SavedAnswerDetail(
                        question_id=ans.question_id,
                        question_order=q.question_order if q else 0,
                        dimension=q.dimension if q else "Unknown",
                        value=ans.value,
                        updated_at=ans.updated_at,
                    )
                )

        # Sort saved answers by question order
        saved_details.sort(key=lambda a: a.question_order)

        return AttemptResponse(
            id=attempt.id,
            assessment_version_id=attempt.assessment_version_id,
            version_number=version_number,
            status=attempt.status,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            total_questions=total_questions,
            answered_count=len(saved_details),
            answers=saved_details,
        )
