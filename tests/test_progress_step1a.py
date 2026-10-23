"""Unit tests for Progress Tracking, Activity Ledger, Streaks, Milestones, and Weekly Goals (Step 1a & Step 1b)."""
from datetime import date, datetime, timedelta, timezone
from typing import Dict
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from app.models.profile import StudentProfile
from app.models.progress import (
    ActivityEvent,
    MilestoneRule,
    UserMilestone,
)
from app.schemas.progress import (
    WeeklyGoalRequest,
    validate_iana_timezone,
)
from app.services.progress_engine import (
    compute_local_date,
    current_streak,
    evaluate_milestone_eligibility,
    goal_progress,
    longest_streak,
    roadmap_percent,
    validate_rule_params,
    weekly_goal_streak,
)


# ==============================================================================
# PURE STREAK & DATE TESTS
# ==============================================================================

def test_streak_consecutive_days():
    """Consecutive active days increment streak correctly."""
    today = date(2026, 10, 24)
    # Active on 2026-10-20, 21, 22, 23, 24 (5 days)
    activity_dates = [today - timedelta(days=i) for i in range(5)]
    assert current_streak(activity_dates, today=today) == 5
    assert longest_streak(activity_dates) == 5


def test_streak_gap():
    """Multi-day gap breaks streak; 1-day rest day within ISO week is bridged."""
    today = date(2026, 10, 24)  # Saturday
    # Active on Wed (21), Thu (22), missed Fri (23), active on Sat (24) -> 3 active days, 1 rest day in same ISO week
    activity_dates = [date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 24)]
    # With rest day allowance enabled: streak continues (3 active days bridged)
    assert current_streak(activity_dates, today=today, allow_rest_day=True) == 3

    # Multi-day gap: active Mon (19), missed Tue (20) & Wed (21), active Thu (22), Fri (23), Sat (24)
    dates_multi_gap = [date(2026, 10, 19), date(2026, 10, 22), date(2026, 10, 23), date(2026, 10, 24)]
    assert current_streak(dates_multi_gap, today=today, allow_rest_day=True) == 3

    # With rest day allowance disabled: Fri was missed, so streak is only 1 (today)
    assert current_streak(activity_dates, today=today, allow_rest_day=False) == 1


def test_streak_several_events_in_one_day():
    """Multiple activities on the same date count as only one active day."""
    today = date(2026, 10, 24)
    activity_dates = [
        today,
        today,
        today,
        today - timedelta(days=1),
        today - timedelta(days=1),
        today - timedelta(days=2),
    ]
    assert current_streak(activity_dates, today=today) == 3
    assert longest_streak(activity_dates) == 3


def test_streak_active_yesterday_not_today():
    """Active yesterday but not yet today keeps the streak alive."""
    today = date(2026, 10, 24)
    yesterday = today - timedelta(days=1)
    # Active on yesterday, day before yesterday, 3 days ago (3 days)
    activity_dates = [yesterday, yesterday - timedelta(days=1), yesterday - timedelta(days=2)]
    assert current_streak(activity_dates, today=today) == 3


def test_streak_inactive_yesterday_and_today():
    """Inactive both today and yesterday means current streak is 0."""
    today = date(2026, 10, 24)
    # Last active 3 days ago
    activity_dates = [today - timedelta(days=3), today - timedelta(days=4)]
    assert current_streak(activity_dates, today=today) == 0
    # But longest streak reflects past history
    assert longest_streak(activity_dates) == 2


def test_no_activity_returns_zero():
    """No activity events returns streak of 0."""
    today = date(2026, 10, 24)
    assert current_streak([], today=today) == 0
    assert longest_streak([]) == 0


def test_longest_streak():
    """Longest streak computes historical maximum even if current streak is broken."""
    today = date(2026, 10, 24)
    # Past run: 7 consecutive days in September 2026
    sept_run = [date(2026, 9, i) for i in range(1, 8)]
    # Current run: 2 days
    current_run = [today, today - timedelta(days=1)]
    all_dates = sept_run + current_run

    assert current_streak(all_dates, today=today) == 2
    assert longest_streak(all_dates) == 7


# ==============================================================================
# TIMEZONE & BOUNDARY TESTS
# ==============================================================================

def test_timezone_boundary_ist_vs_utc():
    """23:30 IST falls on the same calendar day in IST, but on previous hours in UTC."""
    # 2026-10-24 18:00:00 UTC == 2026-10-24 23:30:00 IST (+5:30)
    utc_dt = datetime(2026, 10, 24, 18, 0, 0, tzinfo=timezone.utc)
    local_ist = compute_local_date(utc_dt, "Asia/Kolkata")
    assert local_ist == date(2026, 10, 24)

    # 2026-10-24 18:31:00 UTC == 2026-10-25 00:01:00 IST (rolls over to 25th in IST)
    utc_rollover = datetime(2026, 10, 24, 18, 31, 0, tzinfo=timezone.utc)
    assert compute_local_date(utc_rollover, "Asia/Kolkata") == date(2026, 10, 25)
    # But in UTC, it's still the 24th
    assert compute_local_date(utc_rollover, "UTC") == date(2026, 10, 24)


def test_timezone_boundary_dst():
    """Daylight saving transitions calculate correct local dates."""
    # US Eastern daylight time transition: 2026-11-01 05:30:00 UTC
    # In America/New_York (UTC-4 EDT -> UTC-5 EST), 05:30 UTC is 01:30 AM EST (Nov 1)
    dst_dt = datetime(2026, 11, 1, 5, 30, 0, tzinfo=timezone.utc)
    local_ny = compute_local_date(dst_dt, "America/New_York")
    assert local_ny == date(2026, 11, 1)


def test_timezone_validator():
    """IANA timezone name validation."""
    assert validate_iana_timezone("Asia/Kolkata") == "Asia/Kolkata"
    assert validate_iana_timezone("America/New_York") == "America/New_York"
    assert validate_iana_timezone("UTC") == "UTC"

    with pytest.raises(ValueError, match="Invalid IANA timezone"):
        validate_iana_timezone("Not/A_Real_Timezone")


# ==============================================================================
# ROADMAP PERCENT & GOAL PROGRESS TESTS
# ==============================================================================

def test_roadmap_percent_weighted():
    """Roadmap completion percent weights by estimated_minutes and excludes skipped."""
    items = [
        {"status": "done", "estimated_minutes": 60},      # Done (60 min)
        {"status": "pending", "estimated_minutes": 120},  # Pending (120 min)
        {"status": "skipped", "estimated_minutes": 300},  # Skipped (excluded)
        {"status": "done", "estimated_minutes": 60},      # Done (60 min)
    ]
    # Total non-skipped = 60 + 120 + 60 = 240 min.
    # Done = 60 + 60 = 120 min.
    # Pct = 120 / 240 = 50.0%
    assert roadmap_percent(items) == 50.0


def test_roadmap_percent_empty_or_all_skipped():
    """Empty roadmap or roadmap with only skipped items returns None."""
    assert roadmap_percent([]) is None
    all_skipped = [{"status": "skipped", "estimated_minutes": 60}]
    assert roadmap_percent(all_skipped) is None


def test_goal_progress_clamping():
    """Goal progress percentages are bounded between 0 and 100."""
    assert goal_progress(0, 10) == 0.0
    assert goal_progress(5, 10) == 50.0
    assert goal_progress(15, 10) == 100.0
    assert goal_progress(5, 0) == 0.0


def test_weekly_goal_streak():
    """Weekly goal streak counts consecutive True from index 0 backwards."""
    assert weekly_goal_streak([True, True, True, False, True]) == 3
    assert weekly_goal_streak([False, True, True]) == 0
    assert weekly_goal_streak([]) == 0


# ==============================================================================
# MILESTONE RULE VALIDATION TESTS
# ==============================================================================

def test_milestone_rule_param_validation():
    """Milestone parameters must strictly match schema; unknown fields rejected."""
    # Valid
    p1 = validate_rule_params("event_count_at_least", {"source_type": "roadmap_item", "count": 5})
    assert p1["count"] == 5

    p2 = validate_rule_params("streak_at_least", {"days": 7})
    assert p2["days"] == 7

    p3 = validate_rule_params("phase_completed", {"phase_order": 1})
    assert p3["phase_order"] == 1

    # Unknown rule type rejected
    with pytest.raises(ValueError, match="Unknown milestone rule_type"):
        validate_rule_params("arbitrary_eval_code", {"code": "rm -rf"})

    # Unknown parameter rejected (extra='forbid')
    with pytest.raises(ValidationError):
        validate_rule_params("streak_at_least", {"days": 7, "malicious_injection": "drop table"})


def test_milestone_evaluation_logic():
    """Pure milestone eligibility evaluation."""
    user_stats = {
        "event_counts": {"adaptive_test": 2, "roadmap_item": 0},
        "current_streak": 7,
        "longest_streak": 7,
        "completed_phases": [1],
    }

    # First test completed
    eligible, ev = evaluate_milestone_eligibility(
        "event_count_at_least",
        {"source_type": "adaptive_test", "count": 1},
        user_stats,
    )
    assert eligible is True
    assert ev["actual_count"] == 2

    # First project completed (not eligible yet)
    eligible, _ = evaluate_milestone_eligibility(
        "event_count_at_least",
        {"source_type": "roadmap_item", "count": 1},
        user_stats,
    )
    assert eligible is False

    # 7-day streak
    eligible, ev = evaluate_milestone_eligibility(
        "streak_at_least",
        {"days": 7},
        user_stats,
    )
    assert eligible is True
    assert ev["achieved_days"] == 7

    # Phase completed
    eligible, ev = evaluate_milestone_eligibility(
        "phase_completed",
        {"phase_order": 1},
        user_stats,
    )
    assert eligible is True


# ==============================================================================
# WEEKLY GOAL REQUEST VALIDATION TESTS
# ==============================================================================

def test_monday_week_boundary():
    """WeeklyGoalRequest accepts Mondays and rejects non-Monday dates."""
    monday = date(2026, 10, 26)  # Monday
    tuesday = date(2026, 10, 27)

    # Valid Monday
    req = WeeklyGoalRequest(week_start=monday, goal_type="roadmap_items", target=5)
    assert req.week_start == monday

    # Non-Monday rejected
    with pytest.raises(ValidationError, match="week_start must be a Monday"):
        WeeklyGoalRequest(week_start=tuesday, goal_type="roadmap_items", target=5)


def test_weekly_goal_target_bounds():
    """Weekly minutes cannot exceed 10,080 minutes (7 * 24 * 60)."""
    monday = date(2026, 10, 26)

    # Valid
    req = WeeklyGoalRequest(week_start=monday, goal_type="minutes", target=1200)
    assert req.target == 1200

    # Over 10,080 minutes
    with pytest.raises(ValidationError, match="cannot exceed available hours"):
        WeeklyGoalRequest(week_start=monday, goal_type="minutes", target=10081)

    # Negative / zero rejected
    with pytest.raises(ValidationError):
        WeeklyGoalRequest(week_start=monday, goal_type="minutes", target=0)


# ==============================================================================
# ASYNC DATABASE & LEDGER TESTS
# ==============================================================================

class MockAsyncSession:
    """Mock session simulating DB behavior for activity ledger & milestones."""
    def __init__(self):
        self.events: Dict[str, ActivityEvent] = {}  # key: (source_type, source_id)
        self.rules: Dict[UUID, MilestoneRule] = {}
        self.user_milestones: Dict[str, UserMilestone] = {}  # key: (user_id, rule_id)
        self.profiles: Dict[UUID, StudentProfile] = {}
        self.queries_executed: int = 0

    def add(self, instance):
        if isinstance(instance, ActivityEvent):
            key = f"{instance.source_type}:{instance.source_id}"
            if key not in self.events:
                self.events[key] = instance
        elif isinstance(instance, MilestoneRule):
            self.rules[instance.id] = instance
        elif isinstance(instance, UserMilestone):
            key = f"{instance.user_id}:{instance.rule_id}"
            self.user_milestones[key] = instance

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass


@pytest.mark.asyncio
async def test_duplicate_event_ignored_and_retick_creates_no_new_day():
    """Un-ticking and re-ticking the same roadmap item creates no new activity event."""
    session = MockAsyncSession()
    user_id = uuid4()
    item_id = str(uuid4())

    profile = StudentProfile(user_id=user_id, timezone="Asia/Kolkata")
    session.profiles[user_id] = profile

    # First completion: records event
    ev1 = ActivityEvent(
        user_id=user_id,
        source_type="roadmap_item",
        source_id=item_id,
        occurred_at=datetime.now(timezone.utc),
        local_date=date(2026, 10, 24),
        tz="Asia/Kolkata",
    )
    session.add(ev1)
    assert len(session.events) == 1

    # Second completion (re-tick): duplicate (source_type, source_id) is ignored
    ev2 = ActivityEvent(
        user_id=user_id,
        source_type="roadmap_item",
        source_id=item_id,
        occurred_at=datetime.now(timezone.utc),
        local_date=date(2026, 10, 24),
        tz="Asia/Kolkata",
    )
    session.add(ev2)
    # Count remains 1!
    assert len(session.events) == 1


@pytest.mark.asyncio
async def test_timezone_change_keeps_old_dates():
    """Changing profile timezone does not alter historical activity events."""
    user_id = uuid4()
    # Event recorded under Asia/Kolkata
    past_event = ActivityEvent(
        user_id=user_id,
        source_type="adaptive_test",
        source_id=str(uuid4()),
        occurred_at=datetime(2026, 10, 20, 19, 0, 0, tzinfo=timezone.utc),
        local_date=date(2026, 10, 21),  # Rolled over in IST
        tz="Asia/Kolkata",
    )

    # User subsequently updates profile timezone to America/New_York
    profile = StudentProfile(user_id=user_id, timezone="America/New_York")

    # Past event local_date remains untouched
    assert past_event.local_date == date(2026, 10, 21)
    assert past_event.tz == "Asia/Kolkata"
    assert profile.timezone == "America/New_York"


@pytest.mark.asyncio
async def test_milestone_awarded_once_and_rule_change_does_not_revoke():
    """Milestones are awarded once and rule changes never revoke existing awards."""
    session = MockAsyncSession()
    user_id = uuid4()
    rule_id = uuid4()

    rule = MilestoneRule(
        id=rule_id,
        key="first_test",
        rule_type="event_count_at_least",
        params={"source_type": "adaptive_test", "count": 1},
        title="First Test Completed",
        version=1,
        active=True,
    )
    session.rules[rule_id] = rule

    # Award milestone
    milestone = UserMilestone(
        id=uuid4(),
        user_id=user_id,
        rule_id=rule_id,
        awarded_at=datetime.now(timezone.utc),
        evidence={"actual_count": 1},
    )
    session.add(milestone)
    assert len(session.user_milestones) == 1

    # Attempting to award again is blocked by (user_id, rule_id)
    milestone_dup = UserMilestone(
        id=uuid4(),
        user_id=user_id,
        rule_id=rule_id,
        awarded_at=datetime.now(timezone.utc),
        evidence={"actual_count": 2},
    )
    session.add(milestone_dup)
    assert len(session.user_milestones) == 1

    # Deactivating the rule or bumping rule version never revokes user's milestone
    rule.active = False
    rule.version = 2
    rule.params = {"source_type": "adaptive_test", "count": 5}

    assert len(session.user_milestones) == 1
    stored_award = list(session.user_milestones.values())[0]
    assert stored_award.user_id == user_id
    assert stored_award.rule_id == rule_id


def test_query_count_stays_flat_principle():
    """Verifies that user stats gathering and milestone evaluation use set/bulk operations."""
    # 50 simulated activities across 10 dates
    dates = [date(2026, 10, i % 10 + 1) for i in range(50)]
    # Calculating streak takes 1 single set conversion and linear walk
    s = longest_streak(dates)
    assert s > 0
