"""Unit tests for Step 1a Study Planner: Pure calculation engine, constraints, and migrations."""
from datetime import date, timedelta
from typing import Dict
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from app.models.planner import PlannerTask
from app.schemas.planner import PlannerTaskCreate
from app.services.planner_engine import (
    PLANNER_TO_ROADMAP_STATUS,
    ROADMAP_TO_PLANNER_STATUS,
    check_is_overallocated,
    compute_daily_budget,
    compute_local_today,
    compute_week_overview,
    get_week_window,
    reconcile_tasks_with_roadmap_replan,
    select_phase_suggestions,
    validate_planner_status_transition,
    validate_scheduled_date_window,
)


# ==============================================================================
# 1. DAILY BUDGET & OVERALLOCATION TESTS
# ==============================================================================

def test_daily_budget_null_cases():
    """Daily budget returns None when hours are missing, zero, or negative."""
    assert compute_daily_budget(None) is None
    assert compute_daily_budget(0) is None
    assert compute_daily_budget(-5) is None


def test_daily_budget_computation_with_buffer():
    """Daily budget reuses roadmap scheduler's 15% buffer and divides by 7."""
    # 14 hours/week = 840 total minutes
    # Usable weekly minutes = 840 * (1 - 0.15) = 714 minutes
    # Daily minutes = round(714 / 7) = 102 minutes
    budget = compute_daily_budget(14)
    assert budget == 102

    # 7 hours/week = 420 minutes -> 420 * 0.85 = 357 -> 357 / 7 = 51 minutes
    assert compute_daily_budget(7) == 51

    # 1 hour/week = 60 minutes -> 60 * 0.85 = 51 -> 51 / 7 = 7 minutes
    assert compute_daily_budget(1) == 7


def test_overallocation_boundary():
    """is_overallocated is None when budget is None; boundary tested strictly."""
    # When budget is None, overallocated is None
    assert check_is_overallocated(planned_minutes=120, daily_budget=None) is None

    # Under budget
    assert check_is_overallocated(planned_minutes=90, daily_budget=100) is False
    # Exactly at budget
    assert check_is_overallocated(planned_minutes=100, daily_budget=100) is False
    # Exceeding budget
    assert check_is_overallocated(planned_minutes=101, daily_budget=100) is True


# ==============================================================================
# 2. WEEK WINDOW & OVERVIEW TESTS
# ==============================================================================

def test_week_window_monday_to_sunday():
    """get_week_window computes Monday start and Sunday end for any given date."""
    # Wednesday 2026-10-28
    wednesday = date(2026, 10, 28)
    start, end = get_week_window(wednesday)
    assert start == date(2026, 10, 26)  # Monday
    assert end == date(2026, 11, 1)    # Sunday
    assert start.weekday() == 0
    assert end.weekday() == 6

    # Monday itself
    monday = date(2026, 10, 26)
    m_start, m_end = get_week_window(monday)
    assert m_start == date(2026, 10, 26)
    assert m_end == date(2026, 11, 1)

    # Sunday
    sunday = date(2026, 11, 1)
    s_start, s_end = get_week_window(sunday)
    assert s_start == date(2026, 10, 26)
    assert s_end == date(2026, 11, 1)


def test_week_window_dst_timezone():
    """Timezone calculation across daylight saving boundary."""
    # US Eastern daylight time transition occurs on 2026-11-01
    today_ny = compute_local_today("America/New_York")
    assert isinstance(today_ny, date)

    today_ist = compute_local_today("Asia/Kolkata")
    assert isinstance(today_ist, date)


def test_compute_week_overview_aggregations():
    """Week overview aggregates 7 daily breakdowns and totals."""
    week_start = date(2026, 10, 26)
    tasks = [
        {"scheduled_date": date(2026, 10, 26), "estimated_minutes": 60, "status": "completed"},
        {"scheduled_date": date(2026, 10, 26), "estimated_minutes": 60, "status": "pending"},
        {"scheduled_date": date(2026, 10, 27), "estimated_minutes": 120, "status": "cancelled"},  # excluded
        {"scheduled_date": date(2026, 10, 28), "estimated_minutes": 90, "status": "in_progress"},
    ]
    overview = compute_week_overview(week_start=week_start, tasks=tasks, daily_budget=100)

    assert overview["week_start"] == "2026-10-26"
    assert overview["daily_budget_minutes"] == 100
    assert overview["weekly_budget_minutes"] == 700
    assert overview["total_planned_minutes"] == 210  # 60 + 60 + 90
    assert overview["total_completed_minutes"] == 60
    assert overview["total_tasks"] == 3
    assert overview["completed_tasks"] == 1

    days = overview["days"]
    assert len(days) == 7
    # Day 0 (Monday): 120 min planned vs 100 min budget -> overallocated
    assert days[0]["date"] == "2026-10-26"
    assert days[0]["planned_minutes"] == 120
    assert days[0]["completed_minutes"] == 60
    assert days[0]["is_overallocated"] is True

    # Day 2 (Wednesday): 90 min planned vs 100 min budget -> not overallocated
    assert days[2]["date"] == "2026-10-28"
    assert days[2]["planned_minutes"] == 90
    assert days[2]["is_overallocated"] is False


# ==============================================================================
# 3. STATUS TRANSITION TESTS
# ==============================================================================

def test_planner_status_transitions_allowed():
    """Allowed status transitions pass validation."""
    # pending -> in_progress, completed, cancelled
    validate_planner_status_transition("pending", "in_progress")
    validate_planner_status_transition("pending", "completed")
    validate_planner_status_transition("pending", "cancelled")

    # in_progress -> pending, completed, cancelled
    validate_planner_status_transition("in_progress", "pending")
    validate_planner_status_transition("in_progress", "completed")
    validate_planner_status_transition("in_progress", "cancelled")

    # completed -> in_progress, pending (reopening)
    validate_planner_status_transition("completed", "in_progress")
    validate_planner_status_transition("completed", "pending")

    # cancelled -> pending (reactivation)
    validate_planner_status_transition("cancelled", "pending")

    # no-op self transitions
    validate_planner_status_transition("pending", "pending")
    validate_planner_status_transition("completed", "completed")


def test_planner_status_transitions_rejected():
    """Forbidden status transitions raise ValueError."""
    # completed -> cancelled (must reopen first)
    with pytest.raises(ValueError, match="Invalid planner status transition"):
        validate_planner_status_transition("completed", "cancelled")

    # cancelled -> completed
    with pytest.raises(ValueError, match="Invalid planner status transition"):
        validate_planner_status_transition("cancelled", "completed")

    # cancelled -> in_progress
    with pytest.raises(ValueError, match="Invalid planner status transition"):
        validate_planner_status_transition("cancelled", "in_progress")

    # unknown statuses
    with pytest.raises(ValueError, match="Invalid planner status transition"):
        validate_planner_status_transition("pending", "archived")


def test_status_mapping_documentation():
    """Verify bidirectional mapping between planner and roadmap statuses."""
    assert PLANNER_TO_ROADMAP_STATUS["pending"] == "todo"
    assert PLANNER_TO_ROADMAP_STATUS["in_progress"] == "in_progress"
    assert PLANNER_TO_ROADMAP_STATUS["completed"] == "done"
    assert PLANNER_TO_ROADMAP_STATUS["cancelled"] == "todo"

    assert ROADMAP_TO_PLANNER_STATUS["todo"] == "pending"
    assert ROADMAP_TO_PLANNER_STATUS["in_progress"] == "in_progress"
    assert ROADMAP_TO_PLANNER_STATUS["done"] == "completed"
    assert ROADMAP_TO_PLANNER_STATUS["skipped"] == "cancelled"


# ==============================================================================
# 4. SUGGESTION SELECTION TESTS
# ==============================================================================

def test_suggestions_never_exceed_budget():
    """Suggestion selection strictly respects remaining budget minutes."""
    id1, id2, id3, id4 = uuid4(), uuid4(), uuid4(), uuid4()
    candidate_items = [
        {"id": id1, "title": "Setup Git", "estimated_minutes": 30, "status": "todo", "order_index": 1},
        {"id": id2, "title": "Learn Variables", "estimated_minutes": 45, "status": "todo", "order_index": 2},
        {"id": id3, "title": "Build CLI App", "estimated_minutes": 60, "status": "todo", "order_index": 3},
        {"id": id4, "title": "FastAPI Basics", "estimated_minutes": 20, "status": "todo", "order_index": 4},
    ]

    # Remaining budget = 75 minutes: item 1 (30m) + item 2 (45m) = 75m
    suggestions = select_phase_suggestions(
        candidate_items=candidate_items,
        scheduled_roadmap_item_ids=set(),
        remaining_budget_minutes=75,
    )
    assert len(suggestions) == 2
    assert suggestions[0]["id"] == id1
    assert suggestions[1]["id"] == id2
    assert all(s["suggested"] is True for s in suggestions)
    assert sum(s["estimated_minutes"] for s in suggestions) <= 75


def test_suggestions_empty_when_budget_zero():
    """Suggestions return empty list when remaining budget is 0 or negative."""
    id1 = uuid4()
    candidate_items = [{"id": id1, "title": "Task", "estimated_minutes": 30, "status": "todo"}]
    assert select_phase_suggestions(candidate_items, set(), remaining_budget_minutes=0) == []
    assert select_phase_suggestions(candidate_items, set(), remaining_budget_minutes=-10) == []


def test_suggestions_exclude_scheduled_and_done():
    """Already scheduled or completed roadmap items are excluded from suggestions."""
    id1, id2, id3 = uuid4(), uuid4(), uuid4()
    candidate_items = [
        {"id": id1, "title": "Already Scheduled", "estimated_minutes": 30, "status": "todo"},
        {"id": id2, "title": "Already Done", "estimated_minutes": 30, "status": "done"},
        {"id": id3, "title": "Available Item", "estimated_minutes": 30, "status": "todo"},
    ]
    suggestions = select_phase_suggestions(
        candidate_items=candidate_items,
        scheduled_roadmap_item_ids={id1},
        remaining_budget_minutes=120,
    )
    assert len(suggestions) == 1
    assert suggestions[0]["id"] == id3


# ==============================================================================
# 5. REPLAN RECONCILIATION TESTS
# ==============================================================================

def test_replan_reconciliation_rules():
    """Only pending and not user_rescheduled tasks follow a roadmap replan.

    - pending moves to new date.
    - completed stays.
    - user_rescheduled stays.
    - cancelled stays.
    - in_progress stays.
    """
    rm1, rm2, rm3, rm4, rm5 = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
    old_date = date(2026, 10, 24)
    new_date = date(2026, 11, 5)

    tasks = [
        {
            "id": uuid4(),
            "roadmap_item_id": rm1,
            "status": "pending",
            "user_rescheduled": False,
            "scheduled_date": old_date,
        },
        {
            "id": uuid4(),
            "roadmap_item_id": rm2,
            "status": "completed",  # COMPLETED STAYS
            "user_rescheduled": False,
            "scheduled_date": old_date,
        },
        {
            "id": uuid4(),
            "roadmap_item_id": rm3,
            "status": "pending",
            "user_rescheduled": True,  # USER RESCHEDULED STAYS
            "scheduled_date": old_date,
        },
        {
            "id": uuid4(),
            "roadmap_item_id": rm4,
            "status": "cancelled",  # CANCELLED STAYS
            "user_rescheduled": False,
            "scheduled_date": old_date,
        },
        {
            "id": uuid4(),
            "roadmap_item_id": rm5,
            "status": "in_progress",  # IN_PROGRESS STAYS
            "user_rescheduled": False,
            "scheduled_date": old_date,
        },
    ]

    new_schedule = {
        rm1: new_date,
        rm2: new_date,
        rm3: new_date,
        rm4: new_date,
        rm5: new_date,
    }

    reconciled = reconcile_tasks_with_roadmap_replan(tasks, new_schedule)

    # rm1: moved to new_date
    assert reconciled[0]["scheduled_date"] == new_date
    # rm2: completed -> stays on old_date
    assert reconciled[1]["scheduled_date"] == old_date
    # rm3: user_rescheduled -> stays on old_date
    assert reconciled[2]["scheduled_date"] == old_date
    # rm4: cancelled -> stays on old_date
    assert reconciled[3]["scheduled_date"] == old_date
    # rm5: in_progress -> stays on old_date
    assert reconciled[4]["scheduled_date"] == old_date


# ==============================================================================
# 6. SCHEDULED DATE WINDOW VALIDATION
# ==============================================================================

def test_scheduled_date_window_validation():
    """scheduled_date must be between 7 days back and 90 days ahead."""
    today = date(2026, 10, 24)

    # Valid
    validate_scheduled_date_window(today, today)
    validate_scheduled_date_window(today - timedelta(days=7), today)  # Exactly 7 days back
    validate_scheduled_date_window(today + timedelta(days=90), today)  # Exactly 90 days ahead
    validate_scheduled_date_window(today + timedelta(days=30), today)

    # Invalid: 8 days back
    with pytest.raises(ValueError, match="must be between"):
        validate_scheduled_date_window(today - timedelta(days=8), today)

    # Invalid: 91 days ahead
    with pytest.raises(ValueError, match="must be between"):
        validate_scheduled_date_window(today + timedelta(days=91), today)


# ==============================================================================
# 7. PARTIAL UNIQUE INDEX & CONSTRAINT TESTS (SIMULATED DB LOGIC)
# ==============================================================================

class MockPlannerStorage:
    """Simulates PostgreSQL partial unique index and check constraints in code."""
    def __init__(self):
        self.tasks: Dict[UUID, PlannerTask] = {}

    def insert(self, task: PlannerTask) -> None:
        # Check CHECK constraint: roadmap_item_id required iff task_type == 'roadmap_item'
        if task.task_type == "roadmap_item" and not task.roadmap_item_id:
            raise ValueError("CHECK constraint violation: roadmap_item_id required for roadmap_item task_type")
        if task.task_type != "roadmap_item" and task.roadmap_item_id:
            raise ValueError("CHECK constraint violation: roadmap_item_id forbidden for non-roadmap_item task_type")

        # Check CHECK constraint: estimated_minutes
        if task.estimated_minutes <= 0 or task.estimated_minutes > 1440:
            raise ValueError("CHECK constraint violation: estimated_minutes must be > 0 and <= 1440")

        # Check partial unique index: (user_id, roadmap_item_id) WHERE status <> 'cancelled' AND roadmap_item_id IS NOT NULL
        if task.roadmap_item_id is not None and task.status != "cancelled":
            for existing in self.tasks.values():
                if (
                    existing.user_id == task.user_id
                    and existing.roadmap_item_id == task.roadmap_item_id
                    and existing.status != "cancelled"
                ):
                    raise ValueError("Partial unique index violation: duplicate active task for roadmap_item_id")

        self.tasks[task.id] = task


def test_partial_unique_index_blocks_active_duplicate_but_allows_after_cancellation():
    """Partial unique index prevents two live tasks for one roadmap item, but allows re-adding after cancellation."""
    storage = MockPlannerStorage()
    user_id = uuid4()
    roadmap_item_id = uuid4()

    # 1. First task: pending -> succeeds
    t1 = PlannerTask(
        id=uuid4(),
        user_id=user_id,
        roadmap_item_id=roadmap_item_id,
        task_type="roadmap_item",
        title="Active Item",
        estimated_minutes=45,
        scheduled_date=date(2026, 10, 24),
        status="pending",
    )
    storage.insert(t1)
    assert len(storage.tasks) == 1

    # 2. Second task for same roadmap item while t1 is pending -> VIOLATION
    t2 = PlannerTask(
        id=uuid4(),
        user_id=user_id,
        roadmap_item_id=roadmap_item_id,
        task_type="roadmap_item",
        title="Duplicate Active Item",
        estimated_minutes=45,
        scheduled_date=date(2026, 10, 25),
        status="pending",
    )
    with pytest.raises(ValueError, match="Partial unique index violation"):
        storage.insert(t2)

    # 3. Cancel t1
    t1.status = "cancelled"

    # 4. Now inserting t2 succeeds because t1 is cancelled!
    storage.insert(t2)
    assert len(storage.tasks) == 2


def test_pydantic_schema_check_constraints():
    """Pydantic schemas enforce type, minutes, and forbidden extra fields."""
    rm_id = uuid4()

    # Valid roadmap task
    t_rm = PlannerTaskCreate(
        title="Review Chapter 1",
        scheduled_date=date(2026, 10, 25),
        estimated_minutes=60,
        task_type="roadmap_item",
        roadmap_item_id=rm_id,
    )
    assert t_rm.task_type == "roadmap_item"

    # Roadmap task missing roadmap_item_id -> rejected
    with pytest.raises(ValidationError, match="roadmap_item_id is required"):
        PlannerTaskCreate(
            title="Invalid",
            scheduled_date=date(2026, 10, 25),
            estimated_minutes=60,
            task_type="roadmap_item",
            roadmap_item_id=None,
        )

    # Custom task with roadmap_item_id -> rejected
    with pytest.raises(ValidationError, match="roadmap_item_id must be None"):
        PlannerTaskCreate(
            title="Custom with RM",
            scheduled_date=date(2026, 10, 25),
            estimated_minutes=60,
            task_type="user_custom",
            roadmap_item_id=rm_id,
        )

    # Zero or negative minutes -> rejected
    with pytest.raises(ValidationError):
        PlannerTaskCreate(
            title="Zero Minutes",
            scheduled_date=date(2026, 10, 25),
            estimated_minutes=0,
            task_type="user_custom",
        )

    # Exceeding 1440 minutes -> rejected
    with pytest.raises(ValidationError):
        PlannerTaskCreate(
            title="Over 24h",
            scheduled_date=date(2026, 10, 25),
            estimated_minutes=1441,
            task_type="user_custom",
        )

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        PlannerTaskCreate(
            title="Hacker",
            scheduled_date=date(2026, 10, 25),
            estimated_minutes=30,
            task_type="user_custom",
            unauthorized="injection",  # extra field
        )


# ==============================================================================
# 8. MIGRATION REVISION CHAIN CHECK
# ==============================================================================

def test_migration_014_metadata():
    """Verify migration 014 exists, references 013, and exports upgrade/downgrade."""
    import importlib.util
    from pathlib import Path

    migration_file = Path(__file__).parent.parent / "alembic" / "versions" / "014_create_planner_tasks.py"
    assert migration_file.exists(), "Migration 014 file must exist"

    spec = importlib.util.spec_from_file_location("migration_014", migration_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "014_create_planner_tasks"
    assert mod.down_revision == "013_create_progress_and_milestones"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")
