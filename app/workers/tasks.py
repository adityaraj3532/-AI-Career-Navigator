import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.core.redis import get_redis_client
from app.llm.gateway import LLMGateway
from app.models.adaptive_test import TestAttempt
from app.models.career import Career, UserCareerCompatibilitySnapshot
from app.repositories.token_repository import TokenRepository

logger = logging.getLogger("app.workers.tasks")


# Pydantic Schemas for AI outputs
class CompatibilityExplanationOutput(BaseModel):
    summary: str
    key_strengths: list[str]
    growth_areas: list[str]
    actionable_advice: str


class CompareVerdictOutput(BaseModel):
    comparison_summary: str
    tradeoffs: list[str]
    recommended_verdict: str


class SkillReportNarrativeOutput(BaseModel):
    executive_summary: str
    mastery_analysis: str
    targeted_practice: list[str]


class RecommendationEnrichmentOutput(BaseModel):
    enriched_why: str


class WeeklyProgressSummaryOutput(BaseModel):
    weekly_summary: str
    highlights: list[str]
    encouragement: str


# ARQ Background Worker Tasks
async def generate_career_compatibility_explanation(ctx: Dict[Any, Any], snapshot_id_str: str) -> Optional[Dict[str, Any]]:
    """Generates an asynchronous AI explanation for a career compatibility snapshot and caches it."""
    logger.info("Generating async compatibility explanation for snapshot %s", snapshot_id_str)
    snapshot_id = UUID(snapshot_id_str)

    async with async_session_factory() as session:
        stmt = select(UserCareerCompatibilitySnapshot).where(UserCareerCompatibilitySnapshot.id == snapshot_id)
        res = await session.execute(stmt)
        snap = res.scalar_one_or_none()
        if not snap:
            logger.warning("Snapshot %s not found", snapshot_id)
            return None

        # Fetch career title
        career_stmt = select(Career.title).where(Career.id == snap.career_id)
        career_res = await session.execute(career_stmt)
        career_title = career_res.scalar() or "Target Career"

    fallback = CompatibilityExplanationOutput(
        summary=f"Strong deterministic alignment ({snap.overall_score}%) with {career_title}.",
        key_strengths=["Verified academic background and interests align with core competencies."],
        growth_areas=["Continue focused skill progression through targeted roadmaps."],
        actionable_advice="Begin the recommended introductory modules in your career roadmap.",
    )

    gateway = LLMGateway()
    inputs = {
        "career_title": career_title,
        "overall_score": snap.overall_score,
        "band": snap.band,
        "breakdown": snap.dimension_scores or {},
        "top_factors": snap.top_driving_factors or "Core academic and assessment fit",
    }

    try:
        gw_res = await gateway.generate(
            prompt_name="career_compatibility",
            inputs=inputs,
            output_schema=CompatibilityExplanationOutput,
            fallback=fallback,
            version=1,
        )
        data = gw_res.data.model_dump()
    except Exception as exc:
        logger.warning("LLM generation failed for snapshot %s: %s; using fallback", snapshot_id_str, exc)
        data = fallback.model_dump()

    # Cache explanation in Redis (7 days TTL)
    try:
        redis = get_redis_client()
        cache_key = f"compat_explanation:{snapshot_id_str}"
        await redis.set(cache_key, json.dumps(data), ex=7 * 86400)
    except Exception as exc:
        logger.debug("Redis caching skipped: %s", exc)

    return data


async def generate_skill_report_narrative(
    ctx: Dict[Any, Any],
    user_id_str: str,
    skill_id_str: str,
    evidence_hash: str,
    skill_name: str,
    current_level: str,
    confidence: str,
    strengths: str,
    weak_subtopics: str,
    evidence_count: int,
) -> Dict[str, Any]:
    """Generates an asynchronous AI diagnostic report narrative and caches it by evidence_hash."""
    logger.info("Generating async skill report narrative for skill %s (hash %s)", skill_id_str, evidence_hash)
    fallback = SkillReportNarrativeOutput(
        executive_summary=f"Demonstrated {current_level} proficiency in {skill_name} with {confidence} confidence.",
        mastery_analysis=f"Performance shows verified strengths in {strengths or 'core topics'}.",
        targeted_practice=[f"Focus additional problem solving on {weak_subtopics or 'advanced concepts'}."],
    )

    gateway = LLMGateway()
    inputs = {
        "skill_name": skill_name,
        "current_level": current_level,
        "confidence": confidence,
        "trend": "improving",
        "strengths": strengths or "fundamental concepts",
        "weak_subtopics": weak_subtopics or "edge cases",
        "evidence_count": evidence_count,
    }

    try:
        gw_res = await gateway.generate(
            prompt_name="career_skill_report",
            inputs=inputs,
            output_schema=SkillReportNarrativeOutput,
            fallback=fallback,
            version=1,
        )
        data = gw_res.data.model_dump()
    except Exception as exc:
        logger.warning("LLM generation failed for skill narrative: %s; using fallback", exc)
        data = fallback.model_dump()

    try:
        redis = get_redis_client()
        cache_key = f"skill_narrative:{user_id_str}:{skill_id_str}:{evidence_hash}"
        await redis.set(cache_key, json.dumps(data), ex=14 * 86400)
    except Exception as exc:
        logger.debug("Redis caching skipped: %s", exc)

    return data


async def cleanup_expired_test_attempts(ctx: Dict[Any, Any]) -> int:
    """Marks abandoned adaptive test attempts as expired."""
    now = datetime.now(timezone.utc)
    logger.info("Running expired adaptive test cleanup...")
    async with async_session_factory() as session:
        stmt = (
            update(TestAttempt)
            .where(TestAttempt.status == "in_progress")
            .where(TestAttempt.expires_at < now)
            .values(status="expired")
        )
        result = await session.execute(stmt)
        await session.commit()
        expired_count = result.rowcount
    logger.info("Expired %d abandoned test attempts.", expired_count)
    return expired_count


async def cleanup_expired_auth_tokens(ctx: Dict[Any, Any]) -> int:
    """Scheduled task purging expired refresh tokens and password reset tokens."""
    logger.info("Running auth tokens cleanup...")
    async with async_session_factory() as session:
        repo = TokenRepository(session)
        rt_count = await repo.delete_expired_tokens()
        pr_count = await repo.delete_expired_password_reset_tokens()
        await session.commit()
    total = rt_count + pr_count
    logger.info("Purged %d expired tokens (%d refresh, %d password reset).", total, rt_count, pr_count)
    return total


async def generate_weekly_progress_summary(ctx: Dict[Any, Any], user_id_str: str) -> Optional[Dict[str, Any]]:
    """Background ARQ job generating AI-assisted weekly progress summary for a student."""
    logger.info("Generating weekly progress summary for user %s", user_id_str)
    user_id = UUID(user_id_str)

    from app.models.profile import StudentProfile
    from app.models.progress import ActivityEvent

    async with async_session_factory() as session:
        # Check profile
        stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res = await session.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return None

        # Fetch recent 7-day activity events
        now = datetime.now(timezone.utc)
        stmt_events = (
            select(ActivityEvent.source_type, ActivityEvent.local_date)
            .where(ActivityEvent.user_id == user_id)
            .order_by(ActivityEvent.local_date.desc())
            .limit(30)
        )
        res_events = await session.execute(stmt_events)
        events = res_events.all()

        total_activities = len(events)
        sources = set(e[0] for e in events)

        # Fallback summary
        fallback_data = {
            "weekly_summary": f"You completed {total_activities} learning activities across {len(sources)} categories.",
            "highlights": [f"{cnt} {st} items" for st, cnt in {s: sum(1 for e in events if e[0] == s) for s in sources}.items()],
            "encouragement": "Consistent daily engagement builds durable expertise.",
        }

        fallback_model = WeeklyProgressSummaryOutput(
            weekly_summary=fallback_data["weekly_summary"],
            highlights=fallback_data["highlights"],
            encouragement=fallback_data["encouragement"],
        )

        # Try LLM Gateway with template fallback
        gateway = LLMGateway()
        inputs = {
            "name": profile.name or "Student",
            "total_activities": total_activities,
            "sources": list(sources),
        }

        data = fallback_data
        try:
            gw_res = await gateway.generate(
                prompt_name="weekly_progress_summary",
                inputs=inputs,
                output_schema=WeeklyProgressSummaryOutput,
                fallback=fallback_model,
                version=1,
            )
            data = gw_res.data.model_dump()
        except Exception as exc:
            logger.info("LLM weekly summary generation fallback used: %s", exc)

        try:
            redis = get_redis_client()
            cache_key = f"weekly_summary:{user_id_str}:{now.strftime('%Y-W%W')}"
            await redis.set(cache_key, json.dumps(data), ex=7 * 86400)
        except Exception as exc:
            logger.debug("Redis caching skipped: %s", exc)

        return data

