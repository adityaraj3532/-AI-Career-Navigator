from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import (
    PortfolioProfile,
    PortfolioResponse,
    PortfolioSummary,
    PortfolioSummaryRequest,
    PortfolioSummaryResponse,
    PublicPortfolioProfile,
    PublicPortfolioResponse,
    ResumeExportResponse,
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

    async def get_public_portfolio(self, user_id: UUID) -> PublicPortfolioResponse:
        """Read-only public portfolio view omitting sensitive email/credentials."""
        profile: Optional[StudentProfile] = await self.repo.get_user_profile(user_id)
        skills = await self.repo.get_user_skills(user_id)
        completed_recs = await self.repo.get_completed_recommendations(user_id)
        completed_milestones = await self.repo.get_completed_roadmap_milestones(user_id)
        diagnostic_tests = await self.repo.get_completed_diagnostic_tests(user_id)

        if not profile and not skills and not completed_milestones and not diagnostic_tests:
            # Check if user exists at all
            if hasattr(self.session, "user_repo"):
                user = await self.session.user_repo.get_by_id(user_id)
            else:
                stmt = select(User).where(User.id == user_id)
                res = await self.session.execute(stmt)
                user = res.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        public_profile = PublicPortfolioProfile(
            user_id=user_id,
            education_level=profile.education_level if profile and hasattr(profile, "education_level") else None,
            target_career=profile.target_career if profile and hasattr(profile, "target_career") else None,
            subjects_of_interest=profile.subjects_of_interest if profile else [],
        )

        summary = PortfolioSummary(
            total_skills_tracked=len(skills),
            total_recommendations_completed=len(completed_recs),
            total_milestones_completed=len(completed_milestones),
            total_tests_completed=len(diagnostic_tests),
        )

        return PublicPortfolioResponse(
            profile=public_profile,
            summary=summary,
            skills=skills,
            completed_recommendations=completed_recs,
            completed_milestones=completed_milestones,
            diagnostic_tests=diagnostic_tests,
        )

    async def generate_portfolio_pitch(
        self,
        user: User,
        req: PortfolioSummaryRequest,
    ) -> PortfolioSummaryResponse:
        """Generates an AI-written elevator pitch summarizing achievements."""
        from app.llm.gateway import LLMGateway

        skills = await self.repo.get_user_skills(user.id)
        milestones = await self.repo.get_completed_roadmap_milestones(user.id)
        tests = await self.repo.get_completed_diagnostic_tests(user.id)
        profile = await self.repo.get_user_profile(user.id)

        target_career = (profile.target_career if profile and hasattr(profile, "target_career") else "Software Engineering")
        skill_names = ", ".join(f"{s.name} ({s.current_level})" for s in skills) if skills else "General Computer Science"
        milestone_titles = ", ".join(m.title for m in milestones[:3]) if milestones else "Foundational Coursework"
        test_summaries = ", ".join(f"{t.topic} ({t.demonstrated_level or 'Tested'})" for t in tests[:2]) if tests else "Standard Diagnostic Assessments"

        fallback = PortfolioSummaryResponse(
            elevator_pitch=f"Motivated {user.education_level} student specializing in {target_career}. Proven competency in {skill_names} through hands-on technical milestones and verified diagnostic assessments.",
            key_highlights=[
                f"Mastered core proficiencies in {skill_names}.",
                f"Completed key practical milestones including {milestone_titles}.",
            ],
            suggested_tagline=f"Aspiring {target_career} Professional | Focused on Building High-Impact Solutions",
        )

        try:
            gateway = LLMGateway()
            gw_res = await gateway.generate(
                prompt_name="portfolio_pitch_v1",
                inputs={
                    "target_career": target_career,
                    "skills": skill_names,
                    "completed_items": milestone_titles,
                    "tests": test_summaries,
                },
                output_schema=PortfolioSummaryResponse,
                fallback=fallback,
            )
            return gw_res.data
        except Exception:
            return fallback

    async def export_resume_markdown(self, user: User) -> ResumeExportResponse:
        """Exports a clean, structured Markdown resume from verified portfolio records."""
        profile = await self.repo.get_user_profile(user.id)
        skills = await self.repo.get_user_skills(user.id)
        completed_recs = await self.repo.get_completed_recommendations(user.id)
        milestones = await self.repo.get_completed_roadmap_milestones(user.id)
        tests = await self.repo.get_completed_diagnostic_tests(user.id)

        target = profile.target_career if profile and hasattr(profile, "target_career") else "Engineering Candidate"
        lines = [
            "# Resume: Candidate Portfolio",
            f"**Education Level:** {user.education_level}  ",
            f"**Target Role:** {target}  ",
            "\n## Technical Skills",
        ]
        if skills:
            for s in skills:
                lines.append(f"- **{s.name}**: {s.current_level.capitalize()} ({s.confidence.capitalize()} Confidence, {s.evidence_count} verified evidence items)")
        else:
            lines.append("- Foundational Technical Problem Solving")

        lines.append("\n## Projects & Completed Milestones")
        if milestones:
            for m in milestones:
                lines.append(f"- **{m.title}** ({m.type.capitalize()}) - Topic: {m.topic}")
        else:
            lines.append("- Independent academic problem sets and project labs")

        if completed_recs:
            lines.append("\n## Verified Certificates & Practical Training")
            for r in completed_recs:
                lines.append(f"- **{r.title}** ({r.item_type.capitalize()})")

        if tests:
            lines.append("\n## Diagnostic Assessments")
            for t in tests:
                lines.append(f"- **{t.topic.capitalize()}**: Demonstrated Level: {t.demonstrated_level or 'Evaluated'}, Score: {t.score_percentage or 0}%")

        md_text = "\n".join(lines)
        return ResumeExportResponse(
            markdown_resume=md_text,
            export_format="markdown",
            generated_at=datetime.now(timezone.utc),
        )
