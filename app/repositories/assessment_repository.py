from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import (
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentResult,
    AssessmentVersion,
)
from app.schemas.assessment import AnswerItem


class AssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_version(self) -> Optional[AssessmentVersion]:
        stmt = (
            select(AssessmentVersion)
            .where(AssessmentVersion.is_active.is_(True))
            .order_by(AssessmentVersion.version_number.desc())
            .options(selectinload(AssessmentVersion.questions))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_version_by_id(self, version_id: UUID) -> Optional[AssessmentVersion]:
        stmt = select(AssessmentVersion).where(AssessmentVersion.id == version_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_questions_for_version(self, version_id: UUID) -> List[AssessmentQuestion]:
        stmt = (
            select(AssessmentQuestion)
            .where(AssessmentQuestion.assessment_version_id == version_id)
            .where(AssessmentQuestion.is_active.is_(True))
            .order_by(AssessmentQuestion.question_order.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_active_draft_attempt(self, user_id: UUID) -> Optional[AssessmentAttempt]:
        stmt = (
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user_id)
            .where(AssessmentAttempt.status == "draft")
            .order_by(AssessmentAttempt.started_at.desc())
            .options(
                selectinload(AssessmentAttempt.assessment_version),
                selectinload(AssessmentAttempt.answers).selectinload(AssessmentAnswer.question),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_attempt_by_id(self, attempt_id: UUID, user_id: UUID) -> Optional[AssessmentAttempt]:
        """Strict multi-tenant query: filters by attempt_id AND user_id."""
        stmt = (
            select(AssessmentAttempt)
            .where(AssessmentAttempt.id == attempt_id)
            .where(AssessmentAttempt.user_id == user_id)
            .options(
                selectinload(AssessmentAttempt.assessment_version),
                selectinload(AssessmentAttempt.answers).selectinload(AssessmentAnswer.question),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_attempt(self, user_id: UUID, version_id: UUID) -> AssessmentAttempt:
        attempt = AssessmentAttempt(
            user_id=user_id,
            assessment_version_id=version_id,
            status="draft",
        )
        self.session.add(attempt)
        await self.session.flush()
        await self.session.refresh(attempt)
        return attempt

    async def upsert_answers(self, attempt_id: UUID, answers: List[AnswerItem]) -> None:
        """Upserts draft responses for an active attempt."""
        stmt = select(AssessmentAnswer).where(AssessmentAnswer.attempt_id == attempt_id)
        res = await self.session.execute(stmt)
        existing_by_qid: Dict[UUID, AssessmentAnswer] = {
            ans.question_id: ans for ans in res.scalars().all()
        }

        now = datetime.now(timezone.utc)
        for item in answers:
            if item.question_id in existing_by_qid:
                record = existing_by_qid[item.question_id]
                record.value = item.value
                record.updated_at = now
            else:
                new_ans = AssessmentAnswer(
                    attempt_id=attempt_id,
                    question_id=item.question_id,
                    value=item.value,
                    updated_at=now,
                )
                self.session.add(new_ans)

        await self.session.flush()

    async def get_result_by_attempt_id(self, attempt_id: UUID) -> Optional[AssessmentResult]:
        stmt = select(AssessmentResult).where(AssessmentResult.attempt_id == attempt_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_result_by_id(self, result_id: UUID, user_id: UUID) -> Optional[AssessmentResult]:
        """Strict multi-tenant query: filters by result_id AND user_id."""
        stmt = (
            select(AssessmentResult)
            .where(AssessmentResult.id == result_id)
            .where(AssessmentResult.user_id == user_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_latest_result(self, user_id: UUID) -> Optional[AssessmentResult]:
        stmt = (
            select(AssessmentResult)
            .where(AssessmentResult.user_id == user_id)
            .order_by(AssessmentResult.version.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_results_for_user(self, user_id: UUID) -> List[AssessmentResult]:
        stmt = (
            select(AssessmentResult)
            .where(AssessmentResult.user_id == user_id)
            .order_by(AssessmentResult.version.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_next_result_version(self, user_id: UUID) -> int:
        stmt = select(func.max(AssessmentResult.version)).where(AssessmentResult.user_id == user_id)
        res = await self.session.execute(stmt)
        max_v = res.scalar()
        return (max_v or 0) + 1

    async def save_result(self, result: AssessmentResult) -> AssessmentResult:
        self.session.add(result)
        await self.session.flush()
        await self.session.refresh(result)
        return result
