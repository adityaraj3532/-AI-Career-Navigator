from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill, SkillEvidence, UserSkill
from app.repositories.skill_repository import SkillRepository
from app.schemas.skill_tracker import (
    RecommendedItemResponse,
    SkillReportResponse,
    UserSkillItemResponse,
    UserSkillsListResponse,
)
from app.services.skill_tracker_engine import (
    analyze_subtopics,
    compute_skill_level_and_confidence,
    compute_trend_over_time,
    generate_fallback_report_text,
)


class SkillService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        if hasattr(session, "skill_repo"):
            self.repo = getattr(session, "skill_repo")
        else:
            self.repo = SkillRepository(session)

    async def list_user_skills(self, user_id: UUID) -> UserSkillsListResponse:
        user_skills = await self.repo.get_user_skills(user_id)
        items = [
            UserSkillItemResponse(
                skill_id=us.skill_id,
                skill_slug=us.skill.slug if us.skill else "",
                skill_name=us.skill.name if us.skill else "",
                category=us.skill.category if us.skill else "General",
                current_level=us.current_level,
                confidence=us.confidence,
                updated_at=us.updated_at,
            )
            for us in user_skills
        ]
        return UserSkillsListResponse(skills=items, total_count=len(items))

    async def declare_skill(
        self,
        user_id: UUID,
        level: str,
        skill_id: Optional[UUID] = None,
        skill_slug: Optional[str] = None,
    ) -> UserSkillItemResponse:
        skill: Optional[Skill] = None
        if skill_id:
            skill = await self.repo.get_skill_by_id(skill_id)
        elif skill_slug:
            skill = await self.repo.get_skill_by_slug(skill_slug)

        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found in catalog",
            )

        # Append declaration evidence
        evidence = SkillEvidence(
            user_id=user_id,
            skill_id=skill.id,
            source_type="declared",
            source_id=None,
            score=None,
            level_signal=level,
            subtopic_scores={},
            summary=f"User self-declared {level} proficiency",
        )
        await self.repo.add_evidence(evidence)

        # Recompute aggregate user skill state
        all_evidence = await self.repo.get_skill_evidence_for_user(user_id, skill.id)
        evidence_dicts = [
            {
                "source_type": e.source_type,
                "created_at": e.created_at,
                "level_signal": e.level_signal,
                "score": e.score,
            }
            for e in all_evidence
        ]
        calc_level, calc_confidence, _ = compute_skill_level_and_confidence(evidence_dicts)

        user_skill = await self.repo.upsert_user_skill(
            user_id=user_id,
            skill_id=skill.id,
            current_level=calc_level,
            confidence=calc_confidence,
        )

        return UserSkillItemResponse(
            skill_id=skill.id,
            skill_slug=skill.slug,
            skill_name=skill.name,
            category=skill.category,
            current_level=user_skill.current_level,
            confidence=user_skill.confidence,
            updated_at=user_skill.updated_at,
        )

    async def get_skill_report(
        self,
        user_id: UUID,
        skill_id: UUID,
    ) -> SkillReportResponse:
        skill = await self.repo.get_skill_by_id(skill_id)
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found",
            )

        user_skill = await self.repo.get_user_skill(user_id, skill.id)
        if not user_skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No skill tracker record found for this user",
            )

        all_evidence = await self.repo.get_skill_evidence_for_user(user_id, skill.id)
        evidence_dicts = [
            {
                "source_type": e.source_type,
                "created_at": e.created_at,
                "level_signal": e.level_signal,
                "score": e.score,
                "subtopic_scores": e.subtopic_scores,
            }
            for e in all_evidence
        ]

        # Calculate current level and confidence
        calc_level, calc_confidence, _ = compute_skill_level_and_confidence(evidence_dicts)
        strengths, weak_subtopics = analyze_subtopics(evidence_dicts)
        trend = compute_trend_over_time(evidence_dicts)

        # Code-driven recommendations
        recommended_items: List[RecommendedItemResponse] = []
        for weak in weak_subtopics[:2]:
            recommended_items.append(
                RecommendedItemResponse(
                    title=f"Practice {weak} Fundamentals",
                    type="practice",
                    description=f"Reinforce core concepts and targeted problem solving in {weak}.",
                    target_subtopic=weak,
                )
            )

        if calc_level == "beginner":
            recommended_items.append(
                RecommendedItemResponse(
                    title=f"Intermediate {skill.name} Roadmap Module",
                    type="roadmap_step",
                    description=f"Level up your foundations in {skill.name} to intermediate concepts.",
                )
            )
        elif calc_level == "intermediate":
            recommended_items.append(
                RecommendedItemResponse(
                    title=f"Advanced {skill.name} Deep Dive",
                    type="course",
                    description=f"Master complex architectures and edge cases in {skill.name}.",
                )
            )
        else:
            recommended_items.append(
                RecommendedItemResponse(
                    title=f"Production-Grade {skill.name} Capstone Project",
                    type="project",
                    description=f"Build and benchmark an enterprise-scale solution using {skill.name}.",
                )
            )

        import hashlib
        import json
        from app.core.redis import get_redis_client

        report_text = generate_fallback_report_text(
            skill_name=skill.name,
            level=calc_level,
            confidence=calc_confidence,
            strengths=strengths,
            weaknesses=weak_subtopics,
            evidence_count=len(all_evidence),
        )

        evidence_str = "".join(f"{e.id}:{e.score}:{e.created_at}" for e in all_evidence)
        evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest()[:16]

        status_val = "fallback"
        try:
            redis = get_redis_client()
            cached = await redis.get(f"skill_narrative:{user_id}:{skill.id}:{evidence_hash}")
            if cached:
                cached_obj = json.loads(cached)
                report_text = f"{cached_obj.get('executive_summary', '')}\n\n{cached_obj.get('mastery_analysis', '')}".strip()
                if report_text:
                    status_val = "ready"
        except Exception:
            pass

        return SkillReportResponse(
            skill_id=skill.id,
            skill_slug=skill.slug,
            skill_name=skill.name,
            current_level=calc_level,
            confidence=calc_confidence,
            strengths=strengths,
            weak_subtopics=weak_subtopics,
            trend_over_time=trend,
            recommended_next_items=recommended_items,
            report_status=status_val,
            report_text=report_text,
            evidence_count=len(all_evidence),
        )

    async def ingest_test_result(
        self,
        user_id: UUID,
        attempt_id: UUID,
        topic: str,
        language: Optional[str],
        demonstrated_level: str,
        score_percentage: int,
        subtopic_scores: Dict[str, Any],
    ) -> Optional[UserSkill]:
        """Automatically called from AdaptiveTestService.finish_test in the same transaction."""
        # 1. Check idempotency: if evidence for ("test", attempt_id) already exists, skip
        existing_evidence = await self.repo.get_evidence_by_source("test", attempt_id)
        if existing_evidence:
            return await self.repo.get_user_skill(user_id, existing_evidence.skill_id)

        # 2. Resolve target skill: check language first (e.g. 'python'), then topic (e.g. 'dsa')
        target_skill: Optional[Skill] = None
        if language:
            target_skill = await self.repo.find_skill_by_name_or_alias(language)
        if not target_skill:
            target_skill = await self.repo.find_skill_by_name_or_alias(topic)

        if not target_skill:
            # Topic not mapped to a catalog skill, cannot record evidence
            return None

        # 3. Create and add evidence
        evidence = SkillEvidence(
            user_id=user_id,
            skill_id=target_skill.id,
            source_type="test",
            source_id=attempt_id,
            score=score_percentage,
            level_signal=demonstrated_level,
            subtopic_scores=subtopic_scores,
            summary=f"Adaptive {topic} test completed with score {score_percentage}% ({demonstrated_level})",
        )
        await self.repo.add_evidence(evidence)

        # 4. Recompute user skill level & confidence
        all_evidence = await self.repo.get_skill_evidence_for_user(user_id, target_skill.id)
        evidence_dicts = [
            {
                "source_type": e.source_type,
                "created_at": e.created_at,
                "level_signal": e.level_signal,
                "score": e.score,
            }
            for e in all_evidence
        ]
        calc_level, calc_confidence, _ = compute_skill_level_and_confidence(evidence_dicts)

        return await self.repo.upsert_user_skill(
            user_id=user_id,
            skill_id=target_skill.id,
            current_level=calc_level,
            confidence=calc_confidence,
        )
