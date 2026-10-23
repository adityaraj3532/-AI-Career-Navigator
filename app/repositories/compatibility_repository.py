from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.career import UserCareerCompatibilitySnapshot


class CompatibilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_snapshot(
        self,
        user_id: UUID,
        career_id: UUID,
    ) -> Optional[UserCareerCompatibilitySnapshot]:
        stmt = (
            select(UserCareerCompatibilitySnapshot)
            .where(
                UserCareerCompatibilitySnapshot.user_id == user_id,
                UserCareerCompatibilitySnapshot.career_id == career_id,
            )
            .options(selectinload(UserCareerCompatibilitySnapshot.career))
            .order_by(UserCareerCompatibilitySnapshot.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_history(
        self,
        user_id: UUID,
        career_id: UUID,
    ) -> List[UserCareerCompatibilitySnapshot]:
        stmt = (
            select(UserCareerCompatibilitySnapshot)
            .where(
                UserCareerCompatibilitySnapshot.user_id == user_id,
                UserCareerCompatibilitySnapshot.career_id == career_id,
            )
            .options(selectinload(UserCareerCompatibilitySnapshot.career))
            .order_by(UserCareerCompatibilitySnapshot.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def save_snapshot(
        self,
        snapshot: UserCareerCompatibilitySnapshot,
    ) -> UserCareerCompatibilitySnapshot:
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot
