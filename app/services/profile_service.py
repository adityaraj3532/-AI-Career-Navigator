from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profile_repo = ProfileRepository(session)

    async def get_profile(self, user: User) -> ProfileResponse:
        profile = await self.profile_repo.get_by_user_id(user.id)
        if not profile:
            # Return empty baseline profile
            now = datetime.now(timezone.utc)
            return ProfileResponse(
                id=uuid4(),
                user_id=user.id,
                name=None,
                budget_level=None,
                hours_available_per_week=None,
                subjects_of_interest=[],
                skills=[],
                created_at=now,
                updated_at=now,
            )

        return ProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            budget_level=profile.budget_level,
            hours_available_per_week=profile.hours_available_per_week,
            subjects_of_interest=profile.subjects_of_interest or [],
            skills=profile.skills or [],
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    async def update_profile(self, user: User, req: ProfileUpdateRequest) -> ProfileResponse:
        profile = await self.profile_repo.upsert_profile(
            user_id=user.id,
            name=req.name,
            budget_level=req.budget_level,
            hours_available_per_week=req.hours_available_per_week,
            subjects_of_interest=req.subjects_of_interest,
            skills=req.skills,
        )
        return ProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            budget_level=profile.budget_level,
            hours_available_per_week=profile.hours_available_per_week,
            subjects_of_interest=profile.subjects_of_interest or [],
            skills=profile.skills or [],
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
