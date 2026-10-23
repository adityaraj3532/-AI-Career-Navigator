import random
from datetime import datetime
from typing import List, Optional, Set, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.adaptive_test import TestAttempt, TestAttemptAnswer, TestQuestionBank


class AdaptiveTestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_question_by_id(self, question_id: UUID) -> Optional[TestQuestionBank]:
        stmt = select(TestQuestionBank).where(TestQuestionBank.id == question_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def count_available_questions(
        self,
        topic: str,
        allow_drafts: bool = False,
        language: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(TestQuestionBank).where(TestQuestionBank.topic == topic)
        if not allow_drafts:
            stmt = stmt.where(TestQuestionBank.status == "verified")
        if language is not None:
            stmt = stmt.where(TestQuestionBank.language == language)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def pick_next_question(
        self,
        topic: str,
        target_difficulty: int,
        allow_drafts: bool = False,
        language: Optional[str] = None,
        exclude_question_ids: Optional[Set[UUID]] = None,
        recently_seen_ids: Optional[Set[UUID]] = None,
    ) -> Optional[TestQuestionBank]:
        """
        Picks the next question adaptively:
        1. Filters by topic, target difficulty, language, and status (verified unless allow_drafts).
        2. Excludes already answered question IDs in this attempt.
        3. Prioritizes questions not seen recently by the user.
        4. Randomizes among candidates.
        5. If no questions exist at target difficulty, falls back to adjacent difficulty.
        """
        exclude_set = exclude_question_ids or set()
        recent_set = recently_seen_ids or set()

        # Try target difficulty first, then adjacent difficulties
        candidate_difficulties = [target_difficulty]
        if target_difficulty == 2:
            candidate_difficulties.extend([3, 1])
        elif target_difficulty == 3:
            candidate_difficulties.extend([2, 1])
        else:
            candidate_difficulties.extend([2, 3])

        for diff in candidate_difficulties:
            stmt = (
                select(TestQuestionBank)
                .where(
                    TestQuestionBank.topic == topic,
                    TestQuestionBank.difficulty == diff,
                )
            )
            if not allow_drafts:
                stmt = stmt.where(TestQuestionBank.status == "verified")
            if language is not None:
                stmt = stmt.where(TestQuestionBank.language == language)

            res = await self.session.execute(stmt)
            all_in_diff = [q for q in res.scalars().all() if q.id not in exclude_set]
            if not all_in_diff:
                continue

            # Prioritize not recently seen
            unseen = [q for q in all_in_diff if q.id not in recent_set]
            pool = unseen if unseen else all_in_diff
            return random.choice(pool)

        return None

    async def get_active_attempt(
        self,
        user_id: UUID,
        topic: str,
    ) -> Optional[TestAttempt]:
        stmt = (
            select(TestAttempt)
            .where(
                TestAttempt.user_id == user_id,
                TestAttempt.topic == topic,
                TestAttempt.status == "in_progress",
            )
            .options(
                selectinload(TestAttempt.career),
                selectinload(TestAttempt.answers),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_recent_finished_attempt(
        self,
        user_id: UUID,
        topic: str,
    ) -> Optional[TestAttempt]:
        stmt = (
            select(TestAttempt)
            .where(
                TestAttempt.user_id == user_id,
                TestAttempt.topic == topic,
                TestAttempt.status == "finished",
            )
            .order_by(TestAttempt.finished_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def count_user_starts_since(
        self,
        user_id: UUID,
        since: datetime,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(TestAttempt)
            .where(
                TestAttempt.user_id == user_id,
                TestAttempt.started_at >= since,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_attempt_by_id(
        self,
        attempt_id: UUID,
        eager_load_answers: bool = True,
    ) -> Optional[TestAttempt]:
        stmt = select(TestAttempt).where(TestAttempt.id == attempt_id)
        if eager_load_answers:
            stmt = stmt.options(
                selectinload(TestAttempt.career),
                selectinload(TestAttempt.answers).selectinload(TestAttemptAnswer.question),
            )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_recent_question_ids(
        self,
        user_id: UUID,
        topic: str,
        limit_attempts: int = 3,
    ) -> Set[UUID]:
        recent_attempts_stmt = (
            select(TestAttempt.id)
            .where(TestAttempt.user_id == user_id, TestAttempt.topic == topic)
            .order_by(TestAttempt.started_at.desc())
            .limit(limit_attempts)
        )
        recent_res = await self.session.execute(recent_attempts_stmt)
        attempt_ids = list(recent_res.scalars().all())
        if not attempt_ids:
            return set()

        answers_stmt = select(TestAttemptAnswer.question_id).where(TestAttemptAnswer.attempt_id.in_(attempt_ids))
        ans_res = await self.session.execute(answers_stmt)
        return set(ans_res.scalars().all())

    async def save_attempt(self, attempt: TestAttempt) -> TestAttempt:
        self.session.add(attempt)
        await self.session.commit()
        await self.session.refresh(attempt)
        return attempt

    async def get_answer(
        self,
        attempt_id: UUID,
        question_id: UUID,
    ) -> Optional[TestAttemptAnswer]:
        stmt = (
            select(TestAttemptAnswer)
            .where(
                TestAttemptAnswer.attempt_id == attempt_id,
                TestAttemptAnswer.question_id == question_id,
            )
            .options(selectinload(TestAttemptAnswer.question))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def add_answer(self, answer: TestAttemptAnswer) -> TestAttemptAnswer:
        self.session.add(answer)
        await self.session.commit()
        await self.session.refresh(answer)
        return answer

    async def list_user_attempts(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TestAttempt], int]:
        count_stmt = select(func.count(TestAttempt.id)).where(TestAttempt.user_id == user_id)
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            select(TestAttempt)
            .where(TestAttempt.user_id == user_id)
            .order_by(TestAttempt.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(stmt)
        attempts = list(res.scalars().all())
        return attempts, total
