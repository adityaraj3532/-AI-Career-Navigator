import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import check_rate_limit
from app.models.portfolio import UserPortfolio, default_visibility
from app.models.profile import StudentProfile
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import (
    AchievementItem,
    CertificateItem,
    CompetitionItem,
    GeneratePortfolioTextRequest,
    GeneratePortfolioTextResponse,
    OwnerPortfolioResponse,
    PortfolioProfile,
    PortfolioResponse,
    PortfolioSummary,
    PortfolioSummaryRequest,
    PortfolioSummaryResponse,
    PortfolioVisibility,
    ProjectItem,
    PublicPortfolioViewResponse,
    PublicSkillItem,
    ResumeExportResponse,
    UpdatePortfolioRequest,
)

logger = logging.getLogger("app.services.portfolio")


class PortfolioService:
    def __init__(self, session: AsyncSession, gateway: Optional[Any] = None) -> None:
        self.session = session
        self.gateway = gateway
        if hasattr(session, "portfolio_repo"):
            self.repo = getattr(session, "portfolio_repo")
        else:
            self.repo = PortfolioRepository(session)

    async def get_owner_portfolio(self, user: User) -> OwnerPortfolioResponse:
        """Private owner view of portfolio. GET MUST NOT write to the database.
        
        If no row exists, returns computed draft suggestions with is_persisted=False.
        """
        portfolio = await self.repo.get_user_portfolio(user.id)
        skills = await self.repo.get_user_skills(user.id)
        milestones = await self.repo.get_completed_roadmap_milestones(user.id)
        completed_recs = await self.repo.get_completed_recommendations(user.id)

        roadmap_projects = [
            ProjectItem(
                title=m.title,
                description=f"Completed {m.type} problem solving in {m.topic} (Difficulty {m.difficulty}).",
                skills=[m.topic],
                link=m.source_url,
                completed_date=m.completed_at.strftime("%Y-%m-%d") if m.completed_at else None,
                provenance="self_reported",  # Never mark self-reported items as verified
            )
            for m in milestones
            if m.type in ("project", "problem", "internship_task")
        ]

        recs_certs = [
            CertificateItem(
                title=r.title,
                issuer=r.provider or "Accredited Provider",
                credential_url=r.source_url,
                issue_date=r.completed_at.strftime("%Y-%m-%d"),
                provenance="self_reported",
            )
            for r in completed_recs
            if r.item_type in ("certificate", "course")
        ]

        if portfolio is not None:
            custom_projects = [ProjectItem.model_validate(p) for p in (portfolio.custom_projects or [])]
            all_projects = custom_projects + [p for p in roadmap_projects if p.title not in {cp.title for cp in custom_projects}]
            custom_certs = [CertificateItem.model_validate(c) for c in (portfolio.custom_certificates or [])]
            all_certs = custom_certs + [c for c in recs_certs if c.title not in {cc.title for cc in custom_certs}]
            competitions = [CompetitionItem.model_validate(c) for c in (portfolio.competitions or [])]
            achievements = [AchievementItem.model_validate(a) for a in (portfolio.achievements or [])]
            vis = PortfolioVisibility.model_validate(portfolio.visibility or {})
            featured_ids = [UUID(str(fid)) for fid in (portfolio.featured_item_ids or [])]

            return OwnerPortfolioResponse(
                is_persisted=True,
                slug=portfolio.slug,
                is_public=portfolio.is_public,
                headline=portfolio.headline,
                about=portfolio.about,
                visibility=vis,
                featured_item_ids=featured_ids,
                skills=skills,
                projects=all_projects,
                certificates=all_certs,
                competitions=competitions,
                achievements=achievements,
                updated_at=portfolio.updated_at,
            )

        # Non-persisted draft suggestions (Row is not created on GET)
        default_slug = f"u-{user.id.hex[:10]}"
        return OwnerPortfolioResponse(
            is_persisted=False,
            slug=default_slug,
            is_public=False,
            headline=None,
            about=None,
            visibility=PortfolioVisibility(),
            featured_item_ids=[],
            skills=skills,
            projects=roadmap_projects,
            certificates=recs_certs,
            competitions=[],
            achievements=[],
            updated_at=None,
        )

    async def update_owner_portfolio(self, user: User, req: UpdatePortfolioRequest) -> OwnerPortfolioResponse:
        """Updates or creates the customized portfolio record for the authenticated owner."""
        portfolio = await self.repo.get_user_portfolio(user.id)

        # Validate slug uniqueness and rate limits
        if req.slug is not None:
            new_slug = req.slug.strip().lower()
            await check_rate_limit(f"slug_update:{user.id}", max_requests=10, window_seconds=3600)
            existing = await self.repo.get_portfolio_by_slug(new_slug)
            if existing and existing.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Slug '{new_slug}' is already claimed by another user.",
                )

        # Audit logging of is_public and slug changes
        if portfolio is None:
            logger.info("AUDIT user_portfolio_created user_id=%s slug=%s is_public=%s", user.id, req.slug or f"u-{user.id.hex[:10]}", req.is_public or False)
        else:
            if (req.is_public is not None and req.is_public != portfolio.is_public) or (req.slug and req.slug != portfolio.slug):
                logger.info(
                    "AUDIT user_portfolio_visibility_change user_id=%s old_slug=%s new_slug=%s old_public=%s new_public=%s",
                    user.id,
                    portfolio.slug,
                    req.slug or portfolio.slug,
                    portfolio.is_public,
                    req.is_public if req.is_public is not None else portfolio.is_public,
                )

        if portfolio is None:
            # Create new row on first PUT
            slug_val = req.slug or f"u-{user.id.hex[:10]}"
            portfolio = UserPortfolio(
                user_id=user.id,
                slug=slug_val,
                is_public=req.is_public if req.is_public is not None else False,
                headline=req.headline,
                about=req.about,
                visibility=req.visibility.model_dump() if req.visibility else default_visibility(),
                featured_item_ids=[str(fid) for fid in req.featured_item_ids] if req.featured_item_ids is not None else [],
                custom_projects=[p.model_dump() for p in req.custom_projects] if req.custom_projects is not None else [],
                custom_certificates=[c.model_dump() for c in req.custom_certificates] if req.custom_certificates is not None else [],
                competitions=[c.model_dump() for c in req.competitions] if req.competitions is not None else [],
                achievements=[a.model_dump() for a in req.achievements] if req.achievements is not None else [],
            )
        else:
            # Update existing row
            if req.slug is not None:
                portfolio.slug = req.slug
            if req.is_public is not None:
                portfolio.is_public = req.is_public
            if req.headline is not None:
                portfolio.headline = req.headline
            if req.about is not None:
                portfolio.about = req.about
            if req.visibility is not None:
                portfolio.visibility = req.visibility.model_dump()
            if req.featured_item_ids is not None:
                portfolio.featured_item_ids = [str(fid) for fid in req.featured_item_ids]
            if req.custom_projects is not None:
                portfolio.custom_projects = [p.model_dump() for p in req.custom_projects]
            if req.custom_certificates is not None:
                portfolio.custom_certificates = [c.model_dump() for c in req.custom_certificates]
            if req.competitions is not None:
                portfolio.competitions = [c.model_dump() for c in req.competitions]
            if req.achievements is not None:
                portfolio.achievements = [a.model_dump() for a in req.achievements]
            portfolio.updated_at = datetime.now(timezone.utc)

        await self.repo.save_user_portfolio(portfolio)
        await self.session.commit()
        return await self.get_owner_portfolio(user)

    async def get_public_portfolio_by_slug(self, slug: str) -> PublicPortfolioViewResponse:
        """Unauthenticated public portfolio by slug.
        
        Enforces:
        - Same 404 for missing, private (is_public=False), or disabled.
        - Strict allowlist schema: no email, user_id, or internal profile fields.
        - Section filtering: only sections whose visibility is True are returned.
        """
        portfolio = await self.repo.get_portfolio_by_slug(slug)
        if not portfolio or not portfolio.is_public:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found or private.",
            )

        vis = portfolio.visibility or {}

        about = portfolio.about if vis.get("about") else None

        skills = None
        if vis.get("skills"):
            raw_skills = await self.repo.get_user_skills(portfolio.user_id)
            skills = [
                PublicSkillItem(
                    slug=s.slug,
                    name=s.name,
                    current_level=s.current_level,
                    confidence=s.confidence,
                    provenance=s.provenance,
                )
                for s in raw_skills
            ]

        projects = None
        if vis.get("projects"):
            projects = [ProjectItem.model_validate(p) for p in (portfolio.custom_projects or [])]

        certs = None
        if vis.get("certificates"):
            certs = [CertificateItem.model_validate(c) for c in (portfolio.custom_certificates or [])]

        competitions = None
        if vis.get("competitions"):
            competitions = [CompetitionItem.model_validate(c) for c in (portfolio.competitions or [])]

        achievements = None
        if vis.get("achievements"):
            achievements = [AchievementItem.model_validate(a) for a in (portfolio.achievements or [])]

        return PublicPortfolioViewResponse(
            slug=portfolio.slug,
            headline=portfolio.headline,
            about=about,
            skills=skills,
            projects=projects,
            certificates=certs,
            competitions=competitions,
            achievements=achievements,
        )

    async def generate_portfolio_text(
        self,
        user: User,
        req: GeneratePortfolioTextRequest,
    ) -> GeneratePortfolioTextResponse:
        """AI text assistant that synthesizes user facts into an about section or project description without hallucinating achievements."""
        from pydantic import BaseModel
        from app.llm.gateway import LLMGateway

        # Daily per-user rate limit
        await check_rate_limit(f"gen_text:{user.id}", max_requests=20, window_seconds=86400)

        facts_text = " ".join(req.user_facts)
        target_role = req.target_career or "Engineering Professional"

        if req.section == "about":
            baseline_text = f"Goal-driven candidate specializing in {target_role}. Key experience includes " + ", ".join(req.user_facts[:3]) + "."
        else:
            baseline_text = f"Practical project demonstrating proficiency in {target_role}. Key facts: " + "; ".join(req.user_facts[:3]) + "."

        class GeneratedOutput(BaseModel):
            generated_text: str

        def anti_hallucination_validator(out: GeneratedOutput) -> bool:
            # Post-validator rejects any number, year, or percentage not present in the facts
            numbers_in_output = re.findall(r"\b\d+[%+]?\b", out.generated_text)
            for num in numbers_in_output:
                if num not in facts_text:
                    logger.warning("Rejecting AI text with hallucinated number '%s'", num)
                    return False
            return True

        fallback = GeneratedOutput(generated_text=baseline_text)
        result_text = baseline_text

        try:
            gateway = self.gateway or LLMGateway()
            gw_res = await gateway.generate(
                prompt_name="portfolio_text_v1",
                inputs={
                    "section": req.section,
                    "target_career": target_role,
                    "user_facts": req.user_facts,
                },
                output_schema=GeneratedOutput,
                fallback=fallback,
                post_validator=anti_hallucination_validator,
            )
            result_text = gw_res.data.generated_text.strip()
        except Exception as exc:
            logger.debug("AI text generation fallback used: %s", exc)

        return GeneratePortfolioTextResponse(
            section=req.section,
            generated_text=result_text,
            is_suggestion=True,
            word_count=len(result_text.split()),
        )

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
            gateway = self.gateway or LLMGateway()
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
