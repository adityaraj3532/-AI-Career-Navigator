from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.skill import Skill, SkillEvidence, UserSkill


class SkillRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_skill_by_id(self, skill_id: UUID) -> Optional[Skill]:
        stmt = select(Skill).where(Skill.id == skill_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_skill_by_slug(self, slug: str) -> Optional[Skill]:
        stmt = select(Skill).where(Skill.slug == slug)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def find_skill_by_name_or_alias(self, term: str) -> Optional[Skill]:
        clean_term = term.strip()
        clean_lower = clean_term.lower()

        # 1. Exact match on slug or name
        stmt = select(Skill).where(
            or_(
                func.lower(Skill.slug) == clean_lower,
                func.lower(Skill.name) == clean_lower,
            )
        )
        res = await self.session.execute(stmt)
        skill = res.scalar_one_or_none()
        if skill:
            return skill

        # 2. Check aliases across skills
        stmt = select(Skill)
        res = await self.session.execute(stmt)
        skills = res.scalars().all()
        for s in skills:
            if s.aliases:
                for alias in s.aliases:
                    if str(alias).strip().lower() == clean_lower:
                        return s

        return None

    async def get_user_skills(self, user_id: UUID) -> List[UserSkill]:
        stmt = (
            select(UserSkill)
            .where(UserSkill.user_id == user_id)
            .options(selectinload(UserSkill.skill))
            .order_by(UserSkill.updated_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_user_skill(self, user_id: UUID, skill_id: UUID) -> Optional[UserSkill]:
        stmt = (
            select(UserSkill)
            .where(UserSkill.user_id == user_id, UserSkill.skill_id == skill_id)
            .options(selectinload(UserSkill.skill))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_skill_evidence_for_user(
        self,
        user_id: UUID,
        skill_id: UUID,
    ) -> List[SkillEvidence]:
        stmt = (
            select(SkillEvidence)
            .where(SkillEvidence.user_id == user_id, SkillEvidence.skill_id == skill_id)
            .order_by(SkillEvidence.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_evidence_by_source(
        self,
        source_type: str,
        source_id: UUID,
    ) -> Optional[SkillEvidence]:
        stmt = select(SkillEvidence).where(
            SkillEvidence.source_type == source_type,
            SkillEvidence.source_id == source_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def add_evidence(self, evidence: SkillEvidence) -> SkillEvidence:
        self.session.add(evidence)
        await self.session.flush()
        return evidence

    async def upsert_user_skill(
        self,
        user_id: UUID,
        skill_id: UUID,
        current_level: str,
        confidence: str,
    ) -> UserSkill:
        stmt = select(UserSkill).where(
            UserSkill.user_id == user_id,
            UserSkill.skill_id == skill_id,
        ).options(selectinload(UserSkill.skill))
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if existing:
            existing.current_level = current_level
            existing.confidence = confidence
            existing.updated_at = now
            await self.session.flush()
            return existing
        else:
            new_user_skill = UserSkill(
                user_id=user_id,
                skill_id=skill_id,
                current_level=current_level,
                confidence=confidence,
                updated_at=now,
            )
            self.session.add(new_user_skill)
            await self.session.flush()
            # Eager load skill relationship
            stmt = select(UserSkill).where(UserSkill.id == new_user_skill.id).options(selectinload(UserSkill.skill))
            res = await self.session.execute(stmt)
            return res.scalar_one()
