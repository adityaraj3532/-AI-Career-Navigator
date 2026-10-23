from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.career import Career
from app.models.skill import SkillEvidence
from app.models.user import User
from app.repositories.career_repository import CareerRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.skill_repository import SkillRepository
from app.schemas.recommendation import (
    RecommendationActionResponse,
    RecommendationItemSchema,
    RecommendationListResponse,
)
from app.services.recommendation_engine import (
    filter_recommendation_candidates,
    rank_recommendations,
)
from app.services.skill_tracker_engine import compute_skill_level_and_confidence


class RecommendationService:
    # Per-user sliding window action timestamps for rate-limiting
    _action_history: Dict[UUID, List[datetime]] = {}
    RATE_LIMIT_ACTIONS_PER_MINUTE = 30

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        if hasattr(session, "recommendation_repo"):
            self.repo = getattr(session, "recommendation_repo")
        else:
            self.repo = RecommendationRepository(session)

        if hasattr(session, "career_repo"):
            self.career_repo = getattr(session, "career_repo")
        else:
            self.career_repo = CareerRepository(session)

        if hasattr(session, "profile_repo"):
            self.profile_repo = getattr(session, "profile_repo")
        else:
            self.profile_repo = ProfileRepository(session)

        if hasattr(session, "skill_repo"):
            self.skill_repo = getattr(session, "skill_repo")
        else:
            self.skill_repo = SkillRepository(session)

    def _check_rate_limit(self, user_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        one_min_ago = now - timedelta(minutes=1)
        history = self._action_history.setdefault(user_id, [])
        # Prune old timestamps
        history = [t for t in history if t > one_min_ago]
        self._action_history[user_id] = history

        if len(history) >= self.RATE_LIMIT_ACTIONS_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded for recommendation actions. Please wait a minute.",
            )
        history.append(now)

    async def get_recommendations(
        self,
        user: User,
        career_id: Optional[UUID] = None,
        budget_level: Optional[str] = None,
        location: Optional[str] = None,
        max_hours: Optional[int] = None,
        item_type: Optional[str] = None,
        include_dismissed: bool = False,
        saved_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> RecommendationListResponse:
        settings = get_settings()
        allow_drafts = settings.ALLOW_DRAFT_CAREERS and settings.ENVIRONMENT.lower() == "development"
        now = datetime.now(timezone.utc)

        # 1. User profile and context
        profile = await self.profile_repo.get_by_user_id(user.id)
        effective_budget = budget_level or (profile.budget_level if profile else None)
        effective_hours = max_hours or (profile.hours_available_per_week if profile else None)

        # 2. Target career resolution
        target_career: Optional[Career] = None
        if career_id:
            target_career = await self.career_repo.get_by_id(career_id, allow_drafts=allow_drafts)
        elif profile and profile.subjects_of_interest:
            # Try to match a default career
            careers = await self.career_repo.get_careers(allow_drafts=allow_drafts)
            target_career = careers[0] if careers else None
        else:
            careers = await self.career_repo.get_careers(allow_drafts=allow_drafts)
            target_career = careers[0] if careers else None

        # 3. Check personalization availability
        user_skills = await self.skill_repo.get_user_skills(user.id)
        tested_skill_levels: Dict[str, float] = {}
        for us in user_skills:
            if us.skill and us.confidence in ("medium", "high"):
                slug = us.skill.slug
                lvl_val = 3.0 if us.current_level == "advanced" else (2.0 if us.current_level == "intermediate" else 1.0)
                tested_skill_levels[slug] = lvl_val

        is_personalised = bool(tested_skill_levels or (profile and (profile.skills or profile.budget_level)))

        # 4. Fetch candidate items and user actions in bulk (flat query count)
        user_actions = await self.repo.get_user_actions(user.id)
        candidates = await self.repo.load_all_candidate_items(
            career_id=target_career.id if target_career else None,
            item_type_filter=item_type,
        )

        # 5. Filter candidates
        filtered = filter_recommendation_candidates(
            items=candidates,
            now=now,
            budget_level=effective_budget,
            user_location=location,
            hours_available=effective_hours,
            user_actions=user_actions,
            include_dismissed=include_dismissed,
            saved_only=saved_only,
            allow_drafts=allow_drafts,
        )

        # 6. Rank items
        ranked = rank_recommendations(
            items=filtered,
            target_career_title=target_career.title if target_career else None,
            target_career_id=str(target_career.id) if target_career else None,
            user_skill_levels=tested_skill_levels if is_personalised else None,
            user_budget_level=effective_budget,
            user_location=location,
            hours_available=effective_hours,
            is_personalised=is_personalised,
        )

        # 7. Pagination with stable ordering
        page = max(1, page)
        page_size = max(1, min(50, page_size))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = ranked[start_idx:end_idx]

        schema_items = [
            RecommendationItemSchema(
                id=it["id"],
                item_type=it["item_type"],
                title=it["title"],
                provider=it.get("provider"),
                cost_inr=it.get("cost_inr"),
                is_free=bool(it.get("cost_inr") == 0 and (it.get("status") == "verified" or allow_drafts)),
                duration=it.get("duration"),
                mode=it.get("mode"),
                location=it.get("location"),
                application_deadline=it.get("application_deadline"),
                expires_at=it.get("expires_at"),
                source_url=it.get("source_url"),
                last_verified_at=it.get("last_verified_at"),
                why_it_fits=it.get("why_it_fits", "Recommended for your pathway"),
                user_state=it.get("user_state", "none"),
                match_score=it.get("match_score", 50),
            )
            for it in paged_items
        ]

        return RecommendationListResponse(
            items=schema_items,
            total_count=len(ranked),
            page=page,
            page_size=page_size,
            personalised=is_personalised,
        )

    async def interact_with_recommendation(
        self,
        user: User,
        item_type: str,
        item_id: UUID,
        new_state: str,
    ) -> RecommendationActionResponse:
        self._check_rate_limit(user.id)
        settings = get_settings()
        allow_drafts = settings.ALLOW_DRAFT_CAREERS and settings.ENVIRONMENT.lower() == "development"

        # 1. Verify item exists and is verified
        item = await self.repo.get_item_by_id_and_type(item_type, item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{item_type.title()} item '{item_id}' not found.",
            )

        if not allow_drafts and getattr(item, "status", None) != "verified":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{item_type.title()} item '{item_id}' is not verified.",
            )

        # 2. Update state or restore (idempotent & reversible)
        if new_state == "none":
            await self.repo.delete_action(user.id, item_type, item_id)
            updated_at = datetime.now(timezone.utc)
        else:
            action = await self.repo.upsert_action(user.id, item_type, item_id, new_state)
            updated_at = action.updated_at

        # 3. Hook: If marked "done", record low-weight evidence via Skill Tracker
        if new_state == "done":
            await self._record_completion_skill_evidence(user.id, item_type, item)

        return RecommendationActionResponse(
            item_type=item_type,
            item_id=item_id,
            state=new_state,
            updated_at=updated_at,
        )

    async def _record_completion_skill_evidence(
        self,
        user_id: UUID,
        item_type: str,
        item: Any,
    ) -> None:
        """Record low-weight skill evidence when a recommendation item is marked done."""
        # Find skill from item (e.g. topic or associated career)
        skill_id = getattr(item, "skill_id", None)
        skill_slug = getattr(item, "skill_slug", None)
        title = getattr(item, "title", getattr(item, "name", "Completed Item"))

        skill = None
        if skill_id:
            skill = await self.skill_repo.get_skill_by_id(skill_id)
        elif skill_slug:
            skill = await self.skill_repo.get_skill_by_slug(skill_slug)
        else:
            # Try to match domain, topic, or title
            domain = getattr(item, "domain", getattr(item, "topic", None))
            if domain:
                skill = await self.skill_repo.find_skill_by_name_or_alias(domain)
            if not skill and title:
                skill = await self.skill_repo.find_skill_by_name_or_alias(title)

        if skill:
            source_type = "roadmap" if item_type == "resource" else "project"
            existing = await self.skill_repo.get_evidence_by_source(
                source_type=source_type,
                source_id=item.id,
            )
            if existing:
                return

            evidence = SkillEvidence(
                user_id=user_id,
                skill_id=skill.id,
                source_type=source_type,
                source_id=item.id,
                score=80,
                level_signal="intermediate",
                subtopic_scores={},
                summary=f"Completed {item_type}: {title}",
            )
            await self.skill_repo.add_evidence(evidence)

            # Recompute skill state
            all_ev = await self.skill_repo.get_skill_evidence_for_user(user_id, skill.id)
            ev_dicts = [
                {"source_type": e.source_type, "created_at": e.created_at, "level_signal": e.level_signal, "score": e.score}
                for e in all_ev
            ]
            calc_lvl, calc_conf, _ = compute_skill_level_and_confidence(ev_dicts)
            await self.skill_repo.upsert_user_skill(user_id, skill.id, calc_lvl, calc_conf)
