"""Progress service for aggregating user progress, streaks, roadmap metrics, and goals."""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import StudentProfile
from app.models.progress import (
    ActivityEvent,
    UserMilestone,
    WeeklyGoal,
)
from app.models.roadmap import Roadmap, RoadmapItem
from app.models.skill import UserSkill
from app.models.user import User
from app.schemas.progress import (
    PhaseProgress,
    ProgressSummaryResponse,
    SkillGainedItem,
    UserMilestoneResponse,
    WeeklyGoalRequest,
    WeeklyGoalResponse,
)
from app.services.progress_engine import (
    compute_local_date,
    current_streak,
    get_week_monday,
    goal_progress,
    longest_streak,
    roadmap_percent,
)


class ProgressService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_progress_summary(self, user: User) -> ProgressSummaryResponse:
        """Retrieve complete progress summary for user.

        Guaranteed pure read: NEVER writes or awards milestones in GET.
        Returns 404 if profile does not exist.
        """
        # 1. Ownership & profile existence
        stmt_profile = select(StudentProfile).where(StudentProfile.user_id == user.id)
        res_profile = await self.session.execute(stmt_profile)
        profile = res_profile.scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found.",
            )

        user_tz = profile.timezone or "Asia/Kolkata"
        now = datetime.now(timezone.utc)
        today = compute_local_date(now, user_tz)

        # 2. Activity events & Streaks
        stmt_events = (
            select(ActivityEvent.local_date)
            .where(ActivityEvent.user_id == user.id)
            .order_by(ActivityEvent.local_date.asc())
        )
        res_events = await self.session.execute(stmt_events)
        activity_dates = [d for d in res_events.scalars().all() if d is not None]

        c_streak = current_streak(activity_dates, today=today, allow_rest_day=True)
        l_streak = longest_streak(activity_dates, allow_rest_day=True)

        # 3. Roadmap & Phase Progress
        stmt_roadmap = (
            select(Roadmap)
            .where(Roadmap.user_id == user.id)
            .options(
                selectinload(Roadmap.phases),
                selectinload(Roadmap.items),
            )
            .order_by(Roadmap.created_at.desc())
        )
        res_roadmap = await self.session.execute(stmt_roadmap)
        active_roadmap = res_roadmap.scalars().first()

        phases_progress: List[PhaseProgress] = []
        all_items: List[RoadmapItem] = []

        if active_roadmap and active_roadmap.phases:
            all_items = active_roadmap.items or []
            # Group items by phase_id
            phase_items_map: Dict[UUID, List[RoadmapItem]] = {}
            for it in all_items:
                if it.phase_id:
                    phase_items_map.setdefault(it.phase_id, []).append(it)

            sorted_phases = sorted(active_roadmap.phases, key=lambda p: p.phase_order)
            for phase in sorted_phases:
                p_items = phase_items_map.get(phase.id, [])

                non_skipped = [it for it in p_items if it.status != "skipped"]
                done_items = [it for it in non_skipped if it.status == "done"]
                total_cnt = len(non_skipped)
                done_cnt = len(done_items)

                p_pct = 0.0
                if total_cnt > 0:
                    p_pct = min(100.0, round((done_cnt / total_cnt) * 100.0, 1))

                phases_progress.append(
                    PhaseProgress(
                        phase_id=phase.id,
                        phase_order=phase.phase_order,
                        name=phase.name,
                        total_items=total_cnt,
                        done_items=done_cnt,
                        percent=p_pct,
                    )
                )

        overall_roadmap_pct = roadmap_percent(all_items)

        # 4. Skills Gained
        stmt_skills = (
            select(UserSkill)
            .where(UserSkill.user_id == user.id)
            .order_by(UserSkill.updated_at.desc())
            .limit(10)
        )
        res_skills = await self.session.execute(stmt_skills)
        user_skills = res_skills.scalars().all()

        skills_gained: List[SkillGainedItem] = []
        for us in user_skills:
            provenance = "self_reported"
            if us.level_verified:
                provenance = "test_assessed"
            elif us.evidence_count and us.evidence_count > 0:
                provenance = "interview"

            skills_gained.append(
                SkillGainedItem(
                    skill_name=us.skill_name,
                    level=us.level,
                    provenance=provenance,
                )
            )

        # 5. Milestones Awarded
        stmt_milestones = (
            select(UserMilestone)
            .where(UserMilestone.user_id == user.id)
            .options(selectinload(UserMilestone.rule))
            .order_by(UserMilestone.awarded_at.desc())
        )
        res_milestones = await self.session.execute(stmt_milestones)
        user_milestones = res_milestones.scalars().all()

        milestones_list: List[UserMilestoneResponse] = []
        for um in user_milestones:
            rule_type = um.rule.rule_type if um.rule else "unknown"
            rule_key = um.rule.key if um.rule else "unknown"
            title = um.rule.title if um.rule else "Milestone"

            # Streak badges are labelled as effort badges
            badge_type = "effort" if rule_type == "streak_at_least" else "verified_achievement"

            milestones_list.append(
                UserMilestoneResponse(
                    id=um.id,
                    rule_key=rule_key,
                    title=title,
                    rule_type=rule_type,
                    badge_type=badge_type,
                    awarded_at=um.awarded_at,
                    evidence=um.evidence or {},
                )
            )

        # 6. Weekly Goals for current week
        current_monday = get_week_monday(today)
        next_monday = current_monday + timedelta(days=7)

        stmt_goals = (
            select(WeeklyGoal)
            .where(
                WeeklyGoal.user_id == user.id,
                WeeklyGoal.week_start == current_monday,
            )
        )
        res_goals = await self.session.execute(stmt_goals)
        weekly_goals = res_goals.scalars().all()

        # Compute actual progress for goals in current week
        # Count done roadmap items completed this week
        stmt_done_items = (
            select(RoadmapItem)
            .join(Roadmap, RoadmapItem.roadmap_id == Roadmap.id)
            .where(
                Roadmap.user_id == user.id,
                RoadmapItem.status == "done",
                RoadmapItem.completed_at >= datetime(current_monday.year, current_monday.month, current_monday.day, tzinfo=timezone.utc),
                RoadmapItem.completed_at < datetime(next_monday.year, next_monday.month, next_monday.day, tzinfo=timezone.utc),
            )
        )
        res_done_items = await self.session.execute(stmt_done_items)
        week_done_items = res_done_items.scalars().all()
        week_items_count = len(week_done_items)
        week_minutes = sum(
            (it.estimated_minutes or 30) for it in week_done_items
        )

        goals_list: List[WeeklyGoalResponse] = []
        for g in weekly_goals:
            actual = week_items_count if g.goal_type == "roadmap_items" else week_minutes
            pct = goal_progress(actual, g.target)
            is_completed = actual >= g.target

            goals_list.append(
                WeeklyGoalResponse(
                    id=g.id,
                    week_start=g.week_start,
                    goal_type=g.goal_type,
                    target=g.target,
                    actual=actual,
                    progress_percent=pct,
                    is_completed=is_completed,
                )
            )

        # 7. Neutral weekly summary
        summary_text = self._build_neutral_summary(
            current_streak_val=c_streak,
            done_this_week=week_items_count,
            roadmap_pct=overall_roadmap_pct,
        )

        return ProgressSummaryResponse(
            timezone=user_tz,
            roadmap_percent=overall_roadmap_pct,
            phases=phases_progress,
            skills_gained=skills_gained,
            current_streak=c_streak,
            longest_streak=l_streak,
            milestones=milestones_list,
            weekly_goals=goals_list,
            weekly_summary=summary_text,
        )

    async def upsert_weekly_goal(
        self,
        user: User,
        req: WeeklyGoalRequest,
    ) -> WeeklyGoalResponse:
        """Upsert a weekly goal for current or next week.

        - Rejects past weeks or weeks beyond next week.
        - Targets are bounded.
        """
        stmt_profile = select(StudentProfile).where(StudentProfile.user_id == user.id)
        res_profile = await self.session.execute(stmt_profile)
        profile = res_profile.scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found.",
            )

        user_tz = profile.timezone or "Asia/Kolkata"
        now = datetime.now(timezone.utc)
        today = compute_local_date(now, user_tz)
        current_monday = get_week_monday(today)
        next_monday = current_monday + timedelta(days=7)

        # Only current and next week editable
        if req.week_start < current_monday:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit past week goals ({req.week_start}). Only current week ({current_monday}) and next week ({next_monday}) are editable.",
            )
        if req.week_start > next_monday:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit goals more than one week ahead ({req.week_start}). Editable weeks are {current_monday} and {next_monday}.",
            )

        # Bound minute targets to hours available if configured
        if req.goal_type == "minutes" and profile.hours_available_per_week:
            max_avail_minutes = profile.hours_available_per_week * 60
            if req.target > max_avail_minutes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target ({req.target} minutes) exceeds weekly available hours ({max_avail_minutes} minutes from profile).",
                )

        stmt = (
            insert(WeeklyGoal)
            .values(
                user_id=user.id,
                week_start=req.week_start,
                goal_type=req.goal_type,
                target=req.target,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "week_start", "goal_type"],
                set_={
                    "target": req.target,
                    "updated_at": now,
                },
            )
            .returning(WeeklyGoal)
        )
        res = await self.session.execute(stmt)
        saved_goal = res.scalar_one()
        await self.session.commit()

        # Compute progress
        week_end = req.week_start + timedelta(days=7)
        stmt_done = (
            select(RoadmapItem)
            .join(Roadmap, RoadmapItem.roadmap_id == Roadmap.id)
            .where(
                Roadmap.user_id == user.id,
                RoadmapItem.status == "done",
                RoadmapItem.completed_at >= datetime(req.week_start.year, req.week_start.month, req.week_start.day, tzinfo=timezone.utc),
                RoadmapItem.completed_at < datetime(week_end.year, week_end.month, week_end.day, tzinfo=timezone.utc),
            )
        )
        res_done = await self.session.execute(stmt_done)
        done_items = res_done.scalars().all()

        actual = (
            len(done_items)
            if saved_goal.goal_type == "roadmap_items"
            else sum((it.estimated_minutes or 30) for it in done_items)
        )
        pct = goal_progress(actual, saved_goal.target)

        return WeeklyGoalResponse(
            id=saved_goal.id,
            week_start=saved_goal.week_start,
            goal_type=saved_goal.goal_type,
            target=saved_goal.target,
            actual=actual,
            progress_percent=pct,
            is_completed=actual >= saved_goal.target,
        )

    def _build_neutral_summary(
        self,
        current_streak_val: int,
        done_this_week: int,
        roadmap_pct: Optional[float],
    ) -> str:
        """Generate neutral, non-shaming recap text."""
        parts = []
        if roadmap_pct is not None:
            parts.append(f"Roadmap is {roadmap_pct}% complete.")
        if done_this_week > 0:
            parts.append(f"{done_this_week} item(s) completed this week.")
        if current_streak_val > 0:
            parts.append(f"Active streak: {current_streak_val} day(s).")
        else:
            parts.append("Ready for your next learning step.")

        return " ".join(parts)
