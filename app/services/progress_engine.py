"""Pure calculation engines and rules for streaks, progress, and milestones.

All functions are pure, deterministic, and free of side effects.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

from app.schemas.progress import (
    EventCountParams,
    PhaseCompletedParams,
    StreakParams,
)

# ==============================================================================
# VERSIONED CONFIGURATION
# ==============================================================================

PROGRESS_CONFIG_V1: Dict[str, Any] = {
    "version": "1.0",
    "default_timezone": "Asia/Kolkata",
    "rest_day_allowance": {
        "enabled": True,
        # Rest-day allowance rule:
        # At most 1 rest day per ISO calendar week (Monday to Sunday) is permitted
        # to bridge a single-day gap without breaking the streak.
        # The rest day is not counted as an active day, but preserves continuity.
        "max_rest_days_per_iso_week": 1,
    },
    "default_item_estimated_minutes": 30,
    "max_weekly_minutes": 10080,  # 7 * 24 * 60
}


# ==============================================================================
# TIMEZONE & DATE UTILITIES
# ==============================================================================

def compute_local_date(occurred_at_utc: datetime, tz_str: str) -> date:
    """Convert a UTC datetime into a local calendar date in the given timezone.

    Safe fallback to Asia/Kolkata if timezone name is unrecognized.
    """
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")

    # If datetime is naive, assume UTC
    if occurred_at_utc.tzinfo is None:
        occurred_at_utc = occurred_at_utc.replace(tzinfo=timezone.utc)

    return occurred_at_utc.astimezone(tz).date()


def get_week_monday(d: date) -> date:
    """Return the Monday date of the calendar week for date d."""
    return d - timedelta(days=d.weekday())


# ==============================================================================
# STREAK CALCULATIONS
# ==============================================================================

def current_streak(
    activity_dates: Sequence[date],
    today: date,
    allow_rest_day: bool = True,
) -> int:
    """Calculate the current active streak ending at today or yesterday.

    Streak is alive ONLY IF user was active today or yesterday.
    If inactive both today and yesterday, streak returns 0.
    """
    if not activity_dates:
        return 0

    # Distinct dates sorted ascending, filtered to <= today
    unique_dates = sorted({d for d in activity_dates if d <= today})
    if not unique_dates:
        return 0

    active_set: Set[date] = set(unique_dates)
    yesterday = today - timedelta(days=1)

    # If user was not active today AND not active yesterday, streak is dead (0)
    if today not in active_set and yesterday not in active_set:
        return 0

    # Start backwards from the most recent active date (either today or yesterday)
    start_date = today if today in active_set else yesterday
    cursor = start_date
    streak = 0
    rest_weeks_used: Set[Tuple[int, int]] = set()

    while True:
        if cursor in active_set:
            streak += 1
            cursor = cursor - timedelta(days=1)
        else:
            # Gapped day
            iso_week = (cursor.isocalendar()[0], cursor.isocalendar()[1])
            if allow_rest_day and iso_week not in rest_weeks_used:
                # Allowed rest day: verify that the day before this rest day was active
                day_before = cursor - timedelta(days=1)
                if day_before in active_set:
                    rest_weeks_used.add(iso_week)
                    cursor = day_before
                    continue
                else:
                    # Multi-day gap, streak broken
                    break
            else:
                # No rest day allowance remaining for this week or disabled
                break

    return streak


def longest_streak(
    activity_dates: Sequence[date],
    allow_rest_day: bool = True,
) -> int:
    """Calculate the longest active streak achieved historically.

    Uses rest-day allowance rules if enabled.
    """
    if not activity_dates:
        return 0

    unique_dates = sorted(set(activity_dates))
    if not unique_dates:
        return 0

    active_set: Set[date] = set(unique_dates)
    max_streak = 0

    for start_date in unique_dates:
        streak = 0
        cursor = start_date
        rest_weeks_used: Set[Tuple[int, int]] = set()

        while True:
            if cursor in active_set:
                streak += 1
                cursor = cursor + timedelta(days=1)
            else:
                iso_week = (cursor.isocalendar()[0], cursor.isocalendar()[1])
                if allow_rest_day and iso_week not in rest_weeks_used:
                    day_after = cursor + timedelta(days=1)
                    if day_after in active_set:
                        rest_weeks_used.add(iso_week)
                        cursor = day_after
                        continue
                    else:
                        break
                else:
                    break

        if streak > max_streak:
            max_streak = streak

    return max_streak


def weekly_goal_streak(goal_completions: Sequence[bool]) -> int:
    """Calculate consecutive completed weekly goals from most recent backwards."""
    streak = 0
    for completed in goal_completions:
        if completed:
            streak += 1
        else:
            break
    return streak


def goal_progress(actual: int, target: int) -> float:
    """Calculate percentage progress towards a goal, clamped between 0 and 100."""
    if target <= 0:
        return 0.0
    return min(100.0, round((actual / target) * 100.0, 1))


# ==============================================================================
# ROADMAP PERCENT CALCULATION
# ==============================================================================

def roadmap_percent(items: Sequence[Any]) -> Optional[float]:
    """Calculate weighted percentage completion of a roadmap.

    - Skipped items are excluded from the denominator.
    - Each item is weighted by estimated_minutes (default 30 if null or <= 0).
    - Returns None if the roadmap is empty or if all items are skipped.
    """
    if not items:
        return None

    total_weight = 0
    done_weight = 0
    has_active_item = False

    default_min = PROGRESS_CONFIG_V1["default_item_estimated_minutes"]

    for item in items:
        # Support dict or SQLAlchemy model attribute access
        if isinstance(item, dict):
            status = item.get("status")
            mins = item.get("estimated_minutes")
        else:
            status = getattr(item, "status", None)
            mins = getattr(item, "estimated_minutes", None)

        if status == "skipped":
            continue

        has_active_item = True
        weight = mins if (mins is not None and mins > 0) else default_min
        total_weight += weight

        if status == "done":
            done_weight += weight

    if not has_active_item or total_weight == 0:
        return None

    pct = round((done_weight / total_weight) * 100.0, 1)
    return min(100.0, max(0.0, pct))


# ==============================================================================
# MILESTONE RULE EVALUATION
# ==============================================================================

def validate_rule_params(rule_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that parameters strictly match the Pydantic schema for the rule type.

    Rejects unknown fields or illegal rule types. No eval, no dynamic expressions.
    """
    if rule_type == "event_count_at_least":
        validated = EventCountParams.model_validate(params)
        return validated.model_dump()
    elif rule_type == "streak_at_least":
        validated = StreakParams.model_validate(params)
        return validated.model_dump()
    elif rule_type == "phase_completed":
        validated = PhaseCompletedParams.model_validate(params)
        return validated.model_dump()
    else:
        raise ValueError(f"Unknown milestone rule_type: '{rule_type}'")


def evaluate_milestone_eligibility(
    rule_type: str,
    params: Dict[str, Any],
    user_stats: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """Pure evaluation of whether a user is eligible for a milestone.

    Returns (is_eligible, evidence_dict).
    """
    validated_params = validate_rule_params(rule_type, params)

    if rule_type == "event_count_at_least":
        source_type = validated_params["source_type"]
        required_count = validated_params["count"]
        actual_count = user_stats.get("event_counts", {}).get(source_type, 0)
        if actual_count >= required_count:
            return True, {
                "rule_type": rule_type,
                "source_type": source_type,
                "required_count": required_count,
                "actual_count": actual_count,
            }
        return False, {}

    elif rule_type == "streak_at_least":
        required_days = validated_params["days"]
        current_streak_val = user_stats.get("current_streak", 0)
        longest_streak_val = user_stats.get("longest_streak", 0)
        achieved_days = max(current_streak_val, longest_streak_val)
        if achieved_days >= required_days:
            return True, {
                "rule_type": rule_type,
                "required_days": required_days,
                "achieved_days": achieved_days,
            }
        return False, {}

    elif rule_type == "phase_completed":
        phase_order = validated_params["phase_order"]
        completed_phase_orders = set(user_stats.get("completed_phases", []))
        if phase_order in completed_phase_orders:
            return True, {
                "rule_type": rule_type,
                "phase_order": phase_order,
                "completed": True,
            }
        return False, {}

    return False, {}
