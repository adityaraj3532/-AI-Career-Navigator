"""Pure calculation and validation engine for daily/weekly study planning.

Deterministic, pure business logic for:
1. Status mapping between planner and roadmap tasks.
2. Status transition validations for planner tasks.
3. Daily budget & capacity overallocation calculation reusing roadmap buffer.
4. Monday ISO week window calculation and week overviews across timezones.
5. Suggestion selection from active phase respecting remaining daily budget.
6. Replan reconciliation rules preserving completed and user_rescheduled tasks.
7. Scheduled date window bounds (7 days back to 90 days ahead).
"""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

from app.services.roadmap_engine import BUFFER_PERCENTAGE

# Upper bound on task duration in minutes (24 hours = 1440 minutes)
MAX_TASK_MINUTES = 1440
# Maximum tasks allowed per day per user
MAX_TASKS_PER_DAY = 50
# Window bounds in days
WINDOW_PAST_DAYS = 7
WINDOW_FUTURE_DAYS = 90


# ==============================================================================
# 1. STATUS MAPPING (PLANNER <-> ROADMAP)
# ==============================================================================

PLANNER_TO_ROADMAP_STATUS: Dict[str, str] = {
    "pending": "todo",
    "in_progress": "in_progress",
    "completed": "done",
    "cancelled": "todo",  # Cancelling a planner task returns the roadmap item to backlog/todo
}

ROADMAP_TO_PLANNER_STATUS: Dict[str, str] = {
    "todo": "pending",
    "in_progress": "in_progress",
    "done": "completed",
    "skipped": "cancelled",
}

ALLOWED_PLANNER_TRANSITIONS: Dict[str, Set[str]] = {
    "pending": {"in_progress", "completed", "cancelled"},
    "in_progress": {"pending", "completed", "cancelled"},
    "completed": {"in_progress", "pending"},  # Reopening a completed task
    "cancelled": {"pending"},                 # Reactivating a cancelled task
}


def validate_planner_status_transition(current_status: str, new_status: str) -> None:
    """Validate allowed planner task status transition.

    Raises:
        ValueError: If transition from current_status to new_status is forbidden.
    """
    if current_status == new_status:
        return

    allowed = ALLOWED_PLANNER_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Invalid planner status transition from '{current_status}' to '{new_status}'. Allowed: {sorted(allowed)}"
        )


# ==============================================================================
# 2. DAILY BUDGET & OVERALLOCATION
# ==============================================================================

def compute_daily_budget(hours_available_per_week: Optional[int]) -> Optional[int]:
    """Compute usable daily budget in minutes, reusing roadmap scheduler's 15% buffer.

    - Returns None if hours_available_per_week is None or <= 0.
    - Buffer percentage: 15% reserved for review and unexpected interruptions.
    - Daily usable minutes = round(hours * 60 * (1 - 0.15) / 7).
    """
    if hours_available_per_week is None or hours_available_per_week <= 0:
        return None

    total_weekly_minutes = hours_available_per_week * 60
    usable_weekly_minutes = total_weekly_minutes * (1.0 - BUFFER_PERCENTAGE)
    daily_minutes = int(round(usable_weekly_minutes / 7.0))

    return daily_minutes if daily_minutes > 0 else None


def check_is_overallocated(planned_minutes: int, daily_budget: Optional[int]) -> Optional[bool]:
    """Determine if planned minutes exceed daily budget.

    Returns None if daily_budget is None.
    """
    if daily_budget is None:
        return None
    return planned_minutes > daily_budget


# ==============================================================================
# 3. WEEK WINDOW & OVERVIEW
# ==============================================================================

def get_week_window(target_date: date) -> Tuple[date, date]:
    """Return Monday-start and Sunday-end dates for the ISO week of target_date."""
    week_start = target_date - timedelta(days=target_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def compute_local_today(tz_str: str) -> date:
    """Compute current date in specified IANA timezone with safe fallback to Asia/Kolkata."""
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")
    return datetime.now(timezone.utc).astimezone(tz).date()


def compute_week_overview(
    week_start: date,
    tasks: Sequence[Any],
    daily_budget: Optional[int],
) -> Dict[str, Any]:
    """Compute 7-day breakdown and aggregate weekly metrics.

    Tasks should be for the target week.
    """
    days_data: List[Dict[str, Any]] = []
    total_planned = 0
    total_completed = 0
    total_tasks_cnt = 0
    completed_tasks_cnt = 0

    # Group tasks by scheduled_date
    tasks_by_date: Dict[date, List[Any]] = {}
    for t in tasks:
        s_date = t.get("scheduled_date") if isinstance(t, dict) else getattr(t, "scheduled_date", None)
        if s_date:
            tasks_by_date.setdefault(s_date, []).append(t)

    for i in range(7):
        current_d = week_start + timedelta(days=i)
        day_tasks = tasks_by_date.get(current_d, [])

        active_tasks = [
            t for t in day_tasks
            if (t.get("status") if isinstance(t, dict) else getattr(t, "status", None)) != "cancelled"
        ]
        completed_tasks = [
            t for t in active_tasks
            if (t.get("status") if isinstance(t, dict) else getattr(t, "status", None)) == "completed"
        ]

        day_planned_min = sum(
            (t.get("estimated_minutes", 0) if isinstance(t, dict) else getattr(t, "estimated_minutes", 0))
            for t in active_tasks
        )
        day_completed_min = sum(
            (t.get("estimated_minutes", 0) if isinstance(t, dict) else getattr(t, "estimated_minutes", 0))
            for t in completed_tasks
        )

        overallocated = check_is_overallocated(day_planned_min, daily_budget)

        days_data.append({
            "date": current_d.isoformat(),
            "planned_minutes": day_planned_min,
            "completed_minutes": day_completed_min,
            "total_tasks": len(active_tasks),
            "completed_tasks": len(completed_tasks),
            "is_overallocated": overallocated,
        })

        total_planned += day_planned_min
        total_completed += day_completed_min
        total_tasks_cnt += len(active_tasks)
        completed_tasks_cnt += len(completed_tasks)

    weekly_budget = (daily_budget * 7) if daily_budget is not None else None

    return {
        "week_start": week_start.isoformat(),
        "week_end": (week_start + timedelta(days=6)).isoformat(),
        "daily_budget_minutes": daily_budget,
        "weekly_budget_minutes": weekly_budget,
        "total_planned_minutes": total_planned,
        "total_completed_minutes": total_completed,
        "total_tasks": total_tasks_cnt,
        "completed_tasks": completed_tasks_cnt,
        "days": days_data,
    }


# ==============================================================================
# 4. SUGGESTION SELECTION
# ==============================================================================

def select_phase_suggestions(
    candidate_items: Sequence[Dict[str, Any]],
    scheduled_roadmap_item_ids: Set[Any],
    remaining_budget_minutes: Optional[int],
) -> List[Dict[str, Any]]:
    """Select candidate items from active phase that fit the remaining daily budget.

    - Excludes items already done, skipped, or currently scheduled on any active task.
    - Suggestions never exceed remaining_budget_minutes (if remaining budget is known).
    - If remaining_budget_minutes is None (unspecified hours), returns up to 3 candidate items.
    - Suggestions are returned as dictionary objects marked with suggested=True.
    """
    eligible: List[Dict[str, Any]] = []

    for it in candidate_items:
        it_id = it.get("id")
        status = it.get("status", "todo")

        if it_id in scheduled_roadmap_item_ids:
            continue
        if status in ("done", "skipped"):
            continue

        eligible.append(it)

    # Sort: in_progress first, then order_index / difficulty
    def sort_key(x: Dict[str, Any]):
        status_rank = 0 if x.get("status") == "in_progress" else 1
        return (status_rank, x.get("order_index", 0), x.get("difficulty", 1))

    eligible.sort(key=sort_key)

    suggestions: List[Dict[str, Any]] = []

    if remaining_budget_minutes is not None:
        if remaining_budget_minutes <= 0:
            return []

        accumulated = 0
        for it in eligible:
            mins = it.get("estimated_minutes") or 30
            if accumulated + mins <= remaining_budget_minutes:
                suggestion = dict(it)
                suggestion["suggested"] = True
                suggestions.append(suggestion)
                accumulated += mins
    else:
        # No budget defined: return up to 3 items
        for it in eligible[:3]:
            suggestion = dict(it)
            suggestion["suggested"] = True
            suggestions.append(suggestion)

    return suggestions


# ==============================================================================
# 5. REPLAN RECONCILIATION
# ==============================================================================

def reconcile_tasks_with_roadmap_replan(
    tasks: List[Dict[str, Any]],
    roadmap_item_new_dates: Dict[Any, date],
) -> List[Dict[str, Any]]:
    """Reconcile planner tasks when a roadmap is replanned.

    Rule:
    - ONLY pending and NOT user_rescheduled tasks follow the roadmap replan.
    - Completed tasks are NEVER touched.
    - Cancelled tasks are NEVER touched.
    - user_rescheduled tasks are NEVER touched.
    - in_progress tasks are NOT pending, so they are NEVER moved automatically.
    """
    reconciled: List[Dict[str, Any]] = []

    for t in tasks:
        task_copy = dict(t)
        rm_id = task_copy.get("roadmap_item_id")
        status = task_copy.get("status")
        rescheduled = task_copy.get("user_rescheduled", False)

        if (
            status == "pending"
            and not rescheduled
            and rm_id in roadmap_item_new_dates
        ):
            task_copy["scheduled_date"] = roadmap_item_new_dates[rm_id]

        reconciled.append(task_copy)

    return reconciled


# ==============================================================================
# 6. SCHEDULED DATE WINDOW VALIDATION
# ==============================================================================

def validate_scheduled_date_window(scheduled_date: date, today: date) -> None:
    """Validate that scheduled_date falls within 7 days back to 90 days ahead.

    Raises:
        ValueError: If scheduled_date is outside the permitted window.
    """
    min_date = today - timedelta(days=WINDOW_PAST_DAYS)
    max_date = today + timedelta(days=WINDOW_FUTURE_DAYS)

    if scheduled_date < min_date or scheduled_date > max_date:
        raise ValueError(
            f"scheduled_date ({scheduled_date}) must be between {min_date} (7 days back) and {max_date} (90 days ahead)."
        )
