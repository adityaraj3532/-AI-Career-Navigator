"""Activity ledger and milestone awarding service."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.models.progress import (
    ActivityEvent,
    MilestoneRule,
    UserMilestone,
)
from app.models.roadmap import Roadmap, RoadmapItem, RoadmapPhase
from app.services.progress_engine import (
    compute_local_date,
    current_streak,
    evaluate_milestone_eligibility,
    longest_streak,
    validate_rule_params,
)


async def seed_milestones(session: AsyncSession) -> List[MilestoneRule]:
    """Seed default milestone rules idempotently from milestone_rules.json."""
    seed_path = Path(__file__).parent.parent / "data" / "seed" / "milestone_rules.json"
    if not seed_path.exists():
        return []

    with open(seed_path, "r", encoding="utf-8") as f:
        rules_data = json.load(f)

    seeded_rules: List[MilestoneRule] = []
    now = datetime.now(timezone.utc)

    for item in rules_data:
        # Validate parameters with Pydantic model
        validated_params = validate_rule_params(item["rule_type"], item["params"])

        stmt = select(MilestoneRule).where(MilestoneRule.key == item["key"])
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            # Update title/params if version increased
            existing.title = item["title"]
            existing.params = validated_params
            existing.active = item.get("active", True)
            existing.updated_at = now
            seeded_rules.append(existing)
        else:
            new_rule = MilestoneRule(
                key=item["key"],
                rule_type=item["rule_type"],
                params=validated_params,
                title=item["title"],
                version=item.get("version", 1),
                active=item.get("active", True),
                created_at=now,
                updated_at=now,
            )
            session.add(new_rule)
            seeded_rules.append(new_rule)

    await session.flush()
    return seeded_rules


async def record_activity(
    session: AsyncSession,
    user_id: UUID,
    source_type: str,
    source_id: str,
    occurred_at: Optional[datetime] = None,
    tz_str: Optional[str] = None,
) -> Optional[ActivityEvent]:
    """Record an activity in the ledger in the same transaction as the source event.

    - Server-set timestamp only; no backdating.
    - Resolves user profile timezone if not provided.
    - Computes local_date at insert time; historical records are never mutated on tz change.
    - Idempotent via ON CONFLICT (source_type, source_id) DO NOTHING.
    - Evaluates and awards eligible milestones.
    """
    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc)
    elif occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)

    # Resolve user timezone
    if not tz_str:
        stmt_prof = select(StudentProfile.timezone).where(StudentProfile.user_id == user_id)
        res_prof = await session.execute(stmt_prof)
        tz_str = res_prof.scalar_one_or_none() or "Asia/Kolkata"

    local_date = compute_local_date(occurred_at, tz_str)

    # Insert with ON CONFLICT DO NOTHING on (source_type, source_id)
    stmt = (
        insert(ActivityEvent)
        .values(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            occurred_at=occurred_at,
            local_date=local_date,
            tz=tz_str,
        )
        .on_conflict_do_nothing(
            index_elements=["source_type", "source_id"]
        )
        .returning(ActivityEvent.id)
    )

    result = await session.execute(stmt)
    inserted_id = result.scalar_one_or_none()

    if inserted_id:
        # Trigger milestone evaluation after recording new activity
        await evaluate_and_award_milestones(session, user_id, occurred_at=occurred_at)
        # Fetch the created event
        return await session.get(ActivityEvent, inserted_id)

    return None


async def evaluate_and_award_milestones(
    session: AsyncSession,
    user_id: UUID,
    occurred_at: Optional[datetime] = None,
) -> List[UserMilestone]:
    """Evaluate active milestone rules against user statistics and award new milestones.

    - Milestones are awarded server-side only.
    - Never revoked by later rule changes.
    - Unique constraint (user_id, rule_id) prevents duplicate awards.
    """
    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc)

    # 1. Fetch unawarded active rules
    stmt_rules = (
        select(MilestoneRule)
        .where(
            MilestoneRule.active.is_(True),
            ~MilestoneRule.id.in_(
                select(UserMilestone.rule_id).where(UserMilestone.user_id == user_id)
            ),
        )
    )
    res_rules = await session.execute(stmt_rules)
    unawarded_rules = res_rules.scalars().all()

    if not unawarded_rules:
        return []

    # 2. Gather user stats in bulk to keep query count flat
    user_stats = await _gather_user_stats(session, user_id, occurred_at)

    new_awards: List[UserMilestone] = []
    for rule in unawarded_rules:
        is_eligible, evidence = evaluate_milestone_eligibility(
            rule.rule_type,
            rule.params,
            user_stats,
        )
        if is_eligible:
            milestone = UserMilestone(
                user_id=user_id,
                rule_id=rule.id,
                awarded_at=occurred_at,
                evidence=evidence,
            )
            session.add(milestone)
            new_awards.append(milestone)

    if new_awards:
        await session.flush()

    return new_awards


async def _gather_user_stats(
    session: AsyncSession,
    user_id: UUID,
    occurred_at: datetime,
) -> Dict[str, Any]:
    """Gather aggregated counts, streak dates, and completed phases for a user."""
    # 1. User timezone
    stmt_prof = select(StudentProfile.timezone).where(StudentProfile.user_id == user_id)
    res_prof = await session.execute(stmt_prof)
    tz_str = res_prof.scalar_one_or_none() or "Asia/Kolkata"
    today = compute_local_date(occurred_at, tz_str)

    # 2. Activity events
    stmt_events = (
        select(ActivityEvent.source_type, ActivityEvent.local_date)
        .where(ActivityEvent.user_id == user_id)
        .order_by(ActivityEvent.local_date.asc())
    )
    res_events = await session.execute(stmt_events)
    events = res_events.all()

    event_counts: Dict[str, int] = {}
    activity_dates: List[date] = []
    for source_type, l_date in events:
        event_counts[source_type] = event_counts.get(source_type, 0) + 1
        activity_dates.append(l_date)

    c_streak = current_streak(activity_dates, today=today, allow_rest_day=True)
    l_streak = longest_streak(activity_dates, allow_rest_day=True)

    # 3. Completed roadmap phases
    # A phase is considered completed when it has items, and all non-skipped items are done
    stmt_phases = (
        select(RoadmapPhase.phase_order, RoadmapItem.status)
        .join(Roadmap, RoadmapPhase.roadmap_id == Roadmap.id)
        .join(RoadmapItem, RoadmapItem.phase_id == RoadmapPhase.id)
        .where(Roadmap.user_id == user_id)
    )
    res_phases = await session.execute(stmt_phases)
    phase_rows = res_phases.all()

    phase_items_map: Dict[int, List[str]] = {}
    for p_order, item_status in phase_rows:
        phase_items_map.setdefault(p_order, []).append(item_status)

    completed_phases: List[int] = []
    for p_order, statuses in phase_items_map.items():
        non_skipped = [s for s in statuses if s != "skipped"]
        if non_skipped and all(s == "done" for s in non_skipped):
            completed_phases.append(p_order)

    return {
        "event_counts": event_counts,
        "current_streak": c_streak,
        "longest_streak": l_streak,
        "completed_phases": completed_phases,
    }
