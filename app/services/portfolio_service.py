from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import (
    PortfolioProfile,
    PortfolioResponse,
    PortfolioSummary,
)


class PortfolioService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        if hasattr(session, "portfolio_repo"):
            self.repo = getattr(session, "portfolio_repo")
        else:
            self.repo = PortfolioRepository(session)

    async def get_portfolio_for_user(self, user: User) -> PortfolioResponse:
        """Read-only aggregation of user profile, tracked skills, completed recommendations, milestones, and diagnostic tests."""
        # 1. Fetch user profile
        profile: Optional[StudentProfile] = await self.repo.get_user_profile(user.id)
        portfolio_profile = PortfolioProfile(
            user_id=user.id,
            name=profile.name if profile else None,
            email=user.email,
            education_level=user.education_level,
            target_career=profile.target_career if profile and hasattr(profile, "target_career") else None,
            subjects_of_interest=profile.subjects_of_interest if profile else [],
        )

        # 2. Fetch tracked skills
        skills = await self.repo.get_user_skills(user.id)

        # 3. Fetch completed recommendation items (courses, certs, internships, resources)
        completed_recs = await self.repo.get_completed_recommendations(user.id)

        # 4. Fetch completed roadmap milestones (problems, projects, tasks)
        completed_milestones = await self.repo.get_completed_roadmap_milestones(user.id)

        # 5. Fetch completed diagnostic tests
        diagnostic_tests = await self.repo.get_completed_diagnostic_tests(user.id)

        # 6. Aggregate summary metrics
        summary = PortfolioSummary(
            total_skills_tracked=len(skills),
            total_recommendations_completed=len(completed_recs),
            total_milestones_completed=len(completed_milestones),
            total_tests_completed=len(diagnostic_tests),
        )

        return PortfolioResponse(
            profile=portfolio_profile,
            summary=summary,
            skills=skills,
            completed_recommendations=completed_recs,
            completed_milestones=completed_milestones,
            diagnostic_tests=diagnostic_tests,
        )
