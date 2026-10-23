from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.career import Certificate, Course, Internship
from app.models.recommendation import RecommendationAction
from app.models.roadmap import TemplateItem


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_actions(self, user_id: UUID) -> Dict[Tuple[str, str], str]:
        """Fetch all user recommendation actions in a single query to eliminate N+1."""
        stmt = select(RecommendationAction).where(RecommendationAction.user_id == user_id)
        res = await self.session.execute(stmt)
        actions = res.scalars().all()
        return {(a.item_type, str(a.item_id)): a.state for a in actions}

    async def get_action(
        self,
        user_id: UUID,
        item_type: str,
        item_id: UUID,
    ) -> Optional[RecommendationAction]:
        stmt = select(RecommendationAction).where(
            RecommendationAction.user_id == user_id,
            RecommendationAction.item_type == item_type,
            RecommendationAction.item_id == item_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def upsert_action(
        self,
        user_id: UUID,
        item_type: str,
        item_id: UUID,
        state: str,
    ) -> RecommendationAction:
        action = await self.get_action(user_id, item_type, item_id)
        now = datetime.now(timezone.utc)
        if action:
            action.state = state
            action.updated_at = now
            await self.session.flush()
            return action
        else:
            action = RecommendationAction(
                user_id=user_id,
                item_type=item_type,
                item_id=item_id,
                state=state,
                created_at=now,
                updated_at=now,
            )
            self.session.add(action)
            await self.session.flush()
            return action

    async def delete_action(
        self,
        user_id: UUID,
        item_type: str,
        item_id: UUID,
    ) -> bool:
        action = await self.get_action(user_id, item_type, item_id)
        if action:
            await self.session.delete(action)
            await self.session.flush()
            return True
        return False

    async def get_item_by_id_and_type(
        self,
        item_type: str,
        item_id: UUID,
    ) -> Optional[Any]:
        if item_type == "course":
            stmt = select(Course).where(Course.id == item_id).options(selectinload(Course.careers))
        elif item_type == "certificate":
            stmt = select(Certificate).where(Certificate.id == item_id).options(selectinload(Certificate.careers))
        elif item_type == "internship":
            stmt = select(Internship).where(Internship.id == item_id).options(selectinload(Internship.careers))
        elif item_type == "resource":
            stmt = select(TemplateItem).where(TemplateItem.id == item_id)
        else:
            return None

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def load_all_candidate_items(
        self,
        career_id: Optional[UUID] = None,
        item_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Load candidate courses, certificates, internships, and resources in bulk."""
        candidates: List[Dict[str, Any]] = []

        # 1. Courses (Degrees)
        if item_type_filter in (None, "course"):
            c_stmt = select(Course).options(selectinload(Course.careers))
            res = await self.session.execute(c_stmt)
            for c in res.scalars().all():
                c_ids = [career.id for career in c.careers]
                if career_id and career_id not in c_ids:
                    continue
                candidates.append({
                    "id": c.id,
                    "item_type": "course",
                    "title": c.title,
                    "provider": c.degree_level,
                    "cost_inr": c.cost_inr,
                    "duration": c.duration,
                    "mode": c.mode or "offline",
                    "location": c.location,
                    "eligibility": c.eligibility,
                    "application_deadline": c.application_deadline,
                    "expires_at": c.expires_at,
                    "source_url": c.source_url,
                    "status": c.status,
                    "last_verified_at": c.last_verified_at,
                    "career_ids": c_ids,
                    "domain": c.degree_level,
                })

        # 2. Certificates
        if item_type_filter in (None, "certificate"):
            cert_stmt = select(Certificate).options(selectinload(Certificate.careers))
            res = await self.session.execute(cert_stmt)
            for cert in res.scalars().all():
                c_ids = [career.id for career in cert.careers]
                if career_id and career_id not in c_ids:
                    continue
                candidates.append({
                    "id": cert.id,
                    "item_type": "certificate",
                    "title": cert.name,
                    "provider": cert.issuing_organization,
                    "cost_inr": cert.cost_inr,
                    "duration": cert.duration,
                    "mode": cert.mode or "online",
                    "location": cert.location,
                    "eligibility": cert.eligibility,
                    "application_deadline": cert.application_deadline,
                    "expires_at": cert.expires_at,
                    "source_url": cert.url or cert.source_url,
                    "status": cert.status,
                    "last_verified_at": cert.last_verified_at,
                    "career_ids": c_ids,
                    "domain": cert.issuing_organization,
                })

        # 3. Internships
        if item_type_filter in (None, "internship"):
            i_stmt = select(Internship).options(selectinload(Internship.careers))
            res = await self.session.execute(i_stmt)
            for intern in res.scalars().all():
                c_ids = [career.id for career in intern.careers]
                if career_id and career_id not in c_ids:
                    continue
                dur_str = intern.duration or (f"{intern.duration_months} months" if intern.duration_months else None)
                candidates.append({
                    "id": intern.id,
                    "item_type": "internship",
                    "title": intern.title,
                    "provider": intern.domain,
                    "cost_inr": intern.cost_inr if intern.cost_inr is not None else 0,
                    "duration": dur_str,
                    "mode": intern.mode or ("online" if "Remote" in intern.locations else "offline"),
                    "location": intern.location,
                    "locations": intern.locations,
                    "eligibility": intern.eligibility,
                    "application_deadline": intern.application_deadline,
                    "expires_at": intern.expires_at,
                    "source_url": intern.source_url,
                    "status": intern.status,
                    "last_verified_at": intern.last_verified_at,
                    "career_ids": c_ids,
                    "domain": intern.domain,
                })

        # 4. Free Resources (from template_items)
        if item_type_filter in (None, "resource"):
            r_stmt = select(TemplateItem).where(TemplateItem.type.in_(["video", "problem", "project"]))
            res = await self.session.execute(r_stmt)
            for r in res.scalars().all():
                dur_str = f"{r.estimated_minutes} mins" if r.estimated_minutes else None
                candidates.append({
                    "id": r.id,
                    "item_type": "resource",
                    "title": r.title,
                    "provider": r.topic,
                    "cost_inr": 0,  # Free
                    "duration": dur_str,
                    "mode": "online",
                    "location": None,
                    "eligibility": None,
                    "application_deadline": None,
                    "expires_at": None,
                    "source_url": r.source_url,
                    "status": r.status,
                    "last_verified_at": r.last_verified_at,
                    "career_ids": [],
                    "topic": r.topic,
                })

        return candidates
