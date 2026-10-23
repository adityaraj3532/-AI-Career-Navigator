from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> Optional[StudentProfile]:
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def upsert_profile(
        self,
        user_id: UUID,
        name: Optional[str] = None,
        budget_level: Optional[str] = None,
        hours_available_per_week: Optional[int] = None,
        subjects_of_interest: Optional[List[str]] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
    ) -> StudentProfile:
        profile = await self.get_by_user_id(user_id)
        if not profile:
            profile = StudentProfile(
                user_id=user_id,
                name=name,
                budget_level=budget_level,
                hours_available_per_week=hours_available_per_week,
                subjects_of_interest=subjects_of_interest or [],
                skills=skills or [],
            )
            self.session.add(profile)
        else:
            if name is not None:
                profile.name = name
            if budget_level is not None:
                profile.budget_level = budget_level
            if hours_available_per_week is not None:
                profile.hours_available_per_week = hours_available_per_week
            if subjects_of_interest is not None:
                profile.subjects_of_interest = subjects_of_interest
            if skills is not None:
                profile.skills = skills

        await self.session.commit()
        await self.session.refresh(profile)
        return profile
