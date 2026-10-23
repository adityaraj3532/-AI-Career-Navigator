from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.roadmap import (
    ReplanHistory,
    Roadmap,
    RoadmapItem,
    RoadmapPhase,
    RoadmapTemplate,
)


class RoadmapRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_verified_template(
        self,
        career_id: UUID,
        allow_drafts: bool = False,
    ) -> Optional[RoadmapTemplate]:
        stmt = (
            select(RoadmapTemplate)
            .where(RoadmapTemplate.career_id == career_id)
            .options(
                selectinload(RoadmapTemplate.phases),
                selectinload(RoadmapTemplate.items),
            )
            .order_by(RoadmapTemplate.version.desc())
        )
        if not allow_drafts:
            stmt = stmt.where(RoadmapTemplate.status == "verified")

        res = await self.session.execute(stmt)
        template = res.scalar_one_or_none()
        if not template:
            return None

        # Filter draft items if drafts not allowed
        if not allow_drafts:
            template.items = [it for it in template.items if it.status == "verified"]

        return template

    async def get_active_roadmap_for_user_and_career(
        self,
        user_id: UUID,
        career_id: UUID,
    ) -> Optional[Roadmap]:
        stmt = (
            select(Roadmap)
            .where(
                Roadmap.user_id == user_id,
                Roadmap.career_id == career_id,
                Roadmap.status == "active",
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def count_user_active_roadmaps(self, user_id: UUID) -> int:
        stmt = (
            select(func.count(Roadmap.id))
            .where(Roadmap.user_id == user_id, Roadmap.status == "active")
        )
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def create_cloned_roadmap(
        self,
        roadmap: Roadmap,
        phases: List[RoadmapPhase],
        items: List[RoadmapItem],
    ) -> Roadmap:
        self.session.add(roadmap)
        await self.session.flush()

        for p in phases:
            p.roadmap_id = roadmap.id
            self.session.add(p)
        await self.session.flush()

        for it in items:
            it.roadmap_id = roadmap.id
            self.session.add(it)

        await self.session.commit()
        await self.session.refresh(roadmap)
        return roadmap

    async def get_roadmap_by_id(self, roadmap_id: UUID) -> Optional[Roadmap]:
        stmt = (
            select(Roadmap)
            .where(Roadmap.id == roadmap_id)
            .options(
                selectinload(Roadmap.career),
                selectinload(Roadmap.phases),
                selectinload(Roadmap.items),
                selectinload(Roadmap.replan_history),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_roadmap_item_by_id(self, item_id: UUID) -> Optional[RoadmapItem]:
        stmt = (
            select(RoadmapItem)
            .where(RoadmapItem.id == item_id)
            .options(selectinload(RoadmapItem.roadmap))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def save_roadmap_item(self, item: RoadmapItem) -> RoadmapItem:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def save_replan_history(self, history_record: ReplanHistory) -> ReplanHistory:
        self.session.add(history_record)
        await self.session.commit()
        return history_record
