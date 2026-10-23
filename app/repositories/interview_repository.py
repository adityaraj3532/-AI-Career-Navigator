import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interview import (
    InterviewAnswer,
    InterviewQuestion,
    InterviewResult,
    InterviewSession,
    SessionQuestion,
)
from app.schemas.interview import DimensionScores


class InsufficientQuestionsError(Exception):
    """Raised when the database bank lacks enough verified questions to assemble an interview."""
    pass


class ActiveSessionExistsError(Exception):
    """Raised when a user already has an in-progress active interview session."""
    pass


class InterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_questions_for_interview(
        self,
        career_id: Optional[UUID],
        type: str,
        level: str,
        limit: int = 3,
        allow_drafts: bool = False,
    ) -> List[InterviewQuestion]:
        """Fetches questions matching career, type, and level.

        Draft questions are excluded unless allow_drafts is True.
        """
        stmt = select(InterviewQuestion).where(
            InterviewQuestion.type == type,
            InterviewQuestion.level == level,
        )

        if not allow_drafts:
            stmt = stmt.where(InterviewQuestion.status == "verified")

        if type == "hr":
            # HR questions can be career-specific or generic (career_id is NULL)
            if career_id is not None:
                stmt = stmt.where(
                    or_(
                        InterviewQuestion.career_id == career_id,
                        InterviewQuestion.career_id.is_(None),
                    )
                )
            else:
                stmt = stmt.where(InterviewQuestion.career_id.is_(None))
        else:
            # Technical questions must be tied to the specified career
            if career_id is not None:
                stmt = stmt.where(InterviewQuestion.career_id == career_id)
            else:
                return []

        # Order deterministically by created_at then id
        stmt = stmt.order_by(InterviewQuestion.created_at.asc(), InterviewQuestion.id.asc()).limit(limit)
        res = await self.session.execute(stmt)
        questions = list(res.scalars().all())

        if len(questions) < limit:
            raise InsufficientQuestionsError(
                f"Requested {limit} {type} ({level}) questions, but only found {len(questions)} verified in bank."
            )

        return questions

    async def get_active_session(self, user_id: UUID) -> Optional[InterviewSession]:
        """Finds any active, non-expired interview session for the user."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.status == "in_progress",
                InterviewSession.expires_at > now,
            )
            .options(
                selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.answer),
                selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.results),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_session(
        self,
        user_id: UUID,
        career_id: Optional[UUID],
        type: str,
        level: str,
        questions: List[InterviewQuestion],
        duration_minutes: int = 45,
    ) -> InterviewSession:
        """Creates an interview session and clones question snapshots into session_questions.

        Editing interview_questions later will never modify session_questions.
        """
        existing = await self.get_active_session(user_id)
        if existing:
            raise ActiveSessionExistsError(
                f"User already has an active interview session '{existing.id}' in progress."
            )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=duration_minutes)

        session = InterviewSession(
            id=uuid.uuid4(),
            user_id=user_id,
            career_id=career_id,
            type=type,
            level=level,
            status="in_progress",
            started_at=now,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(session)

        # Snapshot copy of question text and key_points
        session_questions: List[SessionQuestion] = []
        for idx, q in enumerate(questions, start=1):
            sq = SessionQuestion(
                id=uuid.uuid4(),
                session_id=session.id,
                question_id=q.id,
                parent_session_question_id=None,
                order=idx,
                question_text=q.text,
                key_points=list(q.key_points),  # Deep copy snapshot
                is_follow_up=False,
                created_at=now,
            )
            self.session.add(sq)
            session_questions.append(sq)

        session.session_questions = session_questions
        await self.session.flush()
        return session

    async def get_session_by_id(self, session_id: UUID) -> Optional[InterviewSession]:
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.id == session_id)
            .options(
                selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.answer),
                selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.results),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_question_by_id(self, question_id: UUID) -> Optional[InterviewQuestion]:
        stmt = select(InterviewQuestion).where(InterviewQuestion.id == question_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_session_overall_result(self, session_id: UUID) -> Optional[InterviewResult]:
        stmt = select(InterviewResult).where(
            InterviewResult.session_id == session_id,
            InterviewResult.session_question_id.is_(None),
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def save_answer(
        self,
        session_question_id: UUID,
        user_id: UUID,
        answer_text: str,
    ) -> InterviewAnswer:
        now = datetime.now(timezone.utc)
        answer = InterviewAnswer(
            id=uuid.uuid4(),
            session_question_id=session_question_id,
            user_id=user_id,
            answer_text=answer_text[:2000],
            submitted_at=now,
        )
        self.session.add(answer)
        await self.session.flush()
        return answer

    async def save_result(
        self,
        session_id: UUID,
        session_question_id: Optional[UUID],
        rubric_version: str,
        scores: DimensionScores,
        scoring_method: str = "fallback",
        confidence: str = "low",
    ) -> InterviewResult:
        now = datetime.now(timezone.utc)
        result = InterviewResult(
            id=uuid.uuid4(),
            session_id=session_id,
            session_question_id=session_question_id,
            rubric_version=rubric_version,
            coverage_score=scores.coverage_score,
            depth_score=scores.depth_score,
            structure_score=scores.structure_score,
            overall_score=scores.overall_score,
            covered_points=scores.covered_points,
            scoring_method=scoring_method,
            confidence=confidence,
            created_at=now,
        )
        self.session.add(result)
        await self.session.flush()
        return result

    async def add_follow_up_question(
        self,
        session_id: UUID,
        parent_id: UUID,
        order: int,
        question_text: str,
        key_points: List[dict],
    ) -> SessionQuestion:
        now = datetime.now(timezone.utc)
        sq = SessionQuestion(
            id=uuid.uuid4(),
            session_id=session_id,
            question_id=None,
            parent_session_question_id=parent_id,
            order=order,
            question_text=question_text,
            key_points=list(key_points),
            is_follow_up=True,
            created_at=now,
        )
        self.session.add(sq)
        await self.session.flush()
        return sq

    async def get_completed_sessions_for_user(
        self,
        user_id: UUID,
        type: Optional[str] = None,
        career_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[InterviewSession], int]:
        stmt = select(InterviewSession).where(
            InterviewSession.user_id == user_id,
            InterviewSession.status == "completed",
        )
        if type:
            stmt = stmt.where(InterviewSession.type == type)
        if career_id:
            stmt = stmt.where(InterviewSession.career_id == career_id)

        # Count
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar_one() or 0

        # Paginate
        stmt = stmt.order_by(InterviewSession.completed_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

    async def get_completed_sessions_for_analytics(
        self,
        user_id: UUID,
        type: Optional[str] = None,
    ) -> List[InterviewSession]:
        stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.status == "completed",
            )
            .options(
                selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.results),
            )
            .order_by(InterviewSession.completed_at.asc())
        )
        if type:
            stmt = stmt.where(InterviewSession.type == type)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_session(self, session: InterviewSession) -> InterviewSession:
        session.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return session

    async def cleanup_expired_sessions(self) -> int:
        now = datetime.now(timezone.utc)
        stmt = select(InterviewSession).where(
            InterviewSession.status == "in_progress",
            InterviewSession.expires_at < now,
        )
        res = await self.session.execute(stmt)
        expired = list(res.scalars().all())
        for s in expired:
            s.status = "expired"
            s.updated_at = now
        await self.session.flush()
        return len(expired)

