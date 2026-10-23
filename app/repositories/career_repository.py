from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career import Career


class CareerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_careers(self, allow_drafts: bool = False) -> List[Career]:
        """
        Retrieves careers available for scoring and recommendations.
        By default, only verified careers are returned.
        Draft careers are included only if allow_drafts is True.
        """
        stmt = select(Career)
        if not allow_drafts:
            stmt = stmt.where(Career.status == "verified")
        stmt = stmt.order_by(Career.title.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id(self, career_id: UUID) -> Optional[Career]:
        stmt = select(Career).where(Career.id == career_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Career]:
        stmt = select(Career).where(Career.code == code)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
