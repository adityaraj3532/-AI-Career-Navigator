from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.portfolio import UserPortfolio
from app.models.adaptive_test import TestAttempt
from app.models.career import Certificate, Course, Internship
from app.models.profile import StudentProfile
from app.models.recommendation import RecommendationAction
from app.models.roadmap import Roadmap, RoadmapItem, TemplateItem
from app.models.skill import Skill, SkillEvidence, UserSkill
from app.schemas.portfolio import (
    PortfolioCompletedMilestone,
    PortfolioCompletedRecommendation,
    PortfolioDiagnosticTest,
    PortfolioSkillItem,
)


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_profile(self, user_id: UUID) -> Optional[StudentProfile]:
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_skills(self, user_id: UUID) -> List[PortfolioSkillItem]:
        # 1. Fetch user skills with related skill entity
        stmt = (
            select(UserSkill)
            .where(UserSkill.user_id == user_id)
            .options(selectinload(UserSkill.skill))
            .order_by(UserSkill.updated_at.desc())
        )
        res = await self.session.execute(stmt)
        user_skills = list(res.scalars().all())

        if not user_skills:
            return []

        # 2. Evidence count and test provenance per skill in single grouped queries
        skill_ids = [us.skill_id for us in user_skills]
        ev_stmt = (
            select(SkillEvidence.skill_id, func.count(SkillEvidence.id))
            .where(SkillEvidence.user_id == user_id, SkillEvidence.skill_id.in_(skill_ids))
            .group_by(SkillEvidence.skill_id)
        )
        ev_res = await self.session.execute(ev_stmt)
        counts_map: Dict[UUID, int] = dict(ev_res.all())

        test_ev_stmt = (
            select(SkillEvidence.skill_id)
            .where(SkillEvidence.user_id == user_id, SkillEvidence.skill_id.in_(skill_ids), SkillEvidence.source_type == "test")
            .distinct()
        )
        test_ev_res = await self.session.execute(test_ev_stmt)
        test_assessed_skills = set(test_ev_res.scalars().all())

        items = []
        for us in user_skills:
            sk: Optional[Skill] = us.skill
            if not sk:
                continue
            prov: Any = "test_assessed" if us.skill_id in test_assessed_skills else "self_reported"
            items.append(
                PortfolioSkillItem(
                    skill_id=us.skill_id,
                    slug=sk.slug,
                    name=sk.name,
                    current_level=us.current_level,
                    confidence=us.confidence,
                    evidence_count=counts_map.get(us.skill_id, 0),
                    provenance=prov,
                    updated_at=us.updated_at,
                )
            )
        return items

    async def get_completed_recommendations(self, user_id: UUID) -> List[PortfolioCompletedRecommendation]:
        # Fetch actions with state == 'done'
        stmt = (
            select(RecommendationAction)
            .where(RecommendationAction.user_id == user_id, RecommendationAction.state == "done")
            .order_by(RecommendationAction.updated_at.desc())
        )
        res = await self.session.execute(stmt)
        actions = list(res.scalars().all())

        if not actions:
            return []

        # Group by item_type for bulk queries
        courses_ids = [a.item_id for a in actions if a.item_type == "course"]
        certs_ids = [a.item_id for a in actions if a.item_type == "certificate"]
        intern_ids = [a.item_id for a in actions if a.item_type == "internship"]
        res_ids = [a.item_id for a in actions if a.item_type == "resource"]

        items_map: Dict[UUID, Dict[str, Any]] = {}

        if courses_ids:
            c_stmt = select(Course).where(Course.id.in_(courses_ids))
            c_res = await self.session.execute(c_stmt)
            for c in c_res.scalars().all():
                items_map[c.id] = {
                    "title": c.title,
                    "provider": c.degree_level,
                    "source_url": c.source_url,
                }

        if certs_ids:
            cert_stmt = select(Certificate).where(Certificate.id.in_(certs_ids))
            cert_res = await self.session.execute(cert_stmt)
            for cert in cert_res.scalars().all():
                items_map[cert.id] = {
                    "title": cert.name,
                    "provider": cert.issuing_organization,
                    "source_url": cert.url or cert.source_url,
                }

        if intern_ids:
            i_stmt = select(Internship).where(Internship.id.in_(intern_ids))
            i_res = await self.session.execute(i_stmt)
            for intern in i_res.scalars().all():
                items_map[intern.id] = {
                    "title": intern.title,
                    "provider": intern.domain,
                    "source_url": intern.source_url,
                }

        if res_ids:
            r_stmt = select(TemplateItem).where(TemplateItem.id.in_(res_ids))
            r_res = await self.session.execute(r_stmt)
            for r in r_res.scalars().all():
                items_map[r.id] = {
                    "title": r.title,
                    "provider": r.topic,
                    "source_url": r.source_url,
                }

        completed: List[PortfolioCompletedRecommendation] = []
        for a in actions:
            meta = items_map.get(a.item_id, {})
            completed.append(
                PortfolioCompletedRecommendation(
                    item_id=a.item_id,
                    item_type=a.item_type,
                    title=meta.get("title", f"Completed {a.item_type.capitalize()}"),
                    provider=meta.get("provider"),
                    source_url=meta.get("source_url"),
                    completed_at=a.updated_at,
                )
            )
        return completed

    async def get_completed_roadmap_milestones(self, user_id: UUID) -> List[PortfolioCompletedMilestone]:
        stmt = (
            select(RoadmapItem)
            .join(Roadmap, RoadmapItem.roadmap_id == Roadmap.id)
            .where(Roadmap.user_id == user_id, RoadmapItem.status == "done")
            .order_by(RoadmapItem.completed_at.desc().nullslast(), RoadmapItem.updated_at.desc())
        )
        res = await self.session.execute(stmt)
        items = list(res.scalars().all())

        milestones: List[PortfolioCompletedMilestone] = []
        for it in items:
            milestones.append(
                PortfolioCompletedMilestone(
                    item_id=it.id,
                    roadmap_id=it.roadmap_id,
                    type=it.type,
                    title=it.title,
                    topic=it.topic,
                    difficulty=it.difficulty,
                    source_url=it.source_url,
                    completed_at=it.completed_at or it.updated_at,
                )
            )
        return milestones

    async def get_completed_diagnostic_tests(self, user_id: UUID) -> List[PortfolioDiagnosticTest]:
        stmt = (
            select(TestAttempt)
            .where(TestAttempt.user_id == user_id, TestAttempt.status == "finished")
            .order_by(TestAttempt.started_at.desc())
        )
        res = await self.session.execute(stmt)
        attempts = list(res.scalars().all())

        tests: List[PortfolioDiagnosticTest] = []
        for att in attempts:
            tests.append(
                PortfolioDiagnosticTest(
                    attempt_id=att.id,
                    type=att.type,
                    topic=att.topic,
                    demonstrated_level=att.demonstrated_level,
                    confidence=att.confidence,
                    score_percentage=att.score_percentage,
                    completed_at=att.started_at,
                )
            )
        return tests

    async def get_user_portfolio(self, user_id: UUID) -> Optional[UserPortfolio]:
        stmt = select(UserPortfolio).where(UserPortfolio.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_portfolio_by_slug(self, slug: str) -> Optional[UserPortfolio]:
        stmt = select(UserPortfolio).where(func.lower(UserPortfolio.slug) == slug.strip().lower())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def save_user_portfolio(self, portfolio: UserPortfolio) -> UserPortfolio:
        self.session.add(portfolio)
        await self.session.flush()
        await self.session.refresh(portfolio)
        return portfolio
