from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.career import UserShortlist


class ShortlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_count(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(UserShortlist).where(UserShortlist.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_item(self, user_id: UUID, career_id: UUID) -> Optional[UserShortlist]:
        stmt = (
            select(UserShortlist)
            .where(UserShortlist.user_id == user_id, UserShortlist.career_id == career_id)
            .options(selectinload(UserShortlist.career))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> List[UserShortlist]:
        stmt = (
            select(UserShortlist)
            .where(UserShortlist.user_id == user_id)
            .options(selectinload(UserShortlist.career))
            .order_by(UserShortlist.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def add_item(self, user_id: UUID, career_id: UUID) -> UserShortlist:
        existing = await self.get_item(user_id, career_id)
        if existing:
            return existing
        shortlist = UserShortlist(user_id=user_id, career_id=career_id)
        self.session.add(shortlist)
        await self.session.commit()
        return await self.get_item(user_id, career_id) or shortlist

    async def remove_item(self, user_id: UUID, career_id: UUID) -> bool:
        item = await self.get_item(user_id, career_id)
        if not item:
            return False
        await self.session.delete(item)
        await self.session.commit()
        return True
