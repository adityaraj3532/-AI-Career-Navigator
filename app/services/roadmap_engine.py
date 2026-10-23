"""Pure Roadmap Scheduling Engine.

Deterministic, pure business logic for:
1. Validating prerequisite graphs (cycle detection and missing references).
2. Ordering candidate items by prerequisite graph, skill gap, difficulty, and optional flag.
3. Allocating items into weekly capacity with a 15% buffer and overflow to backlog.
4. Handling tested vs declared skill levels (downweighting beginner items only when tested level is higher).
5. Replanning remaining incomplete items from current date while preserving completed/skipped items.
6. Validating item status transition state machine.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo


BUFFER_PERCENTAGE = 0.15  # 15% capacity buffer reserved for reviews / unexpected delays


class CycleError(ValueError):
    """Raised when a circular prerequisite dependency is detected."""
    pass


class MissingReferenceError(ValueError):
    """Raised when an item references a non-existent prerequisite."""
    pass


# ==============================================================================
# 1. PREREQUISITE GRAPH VALIDATION
# ==============================================================================

def validate_prerequisite_graph(items: List[Dict[str, Any]]) -> None:
    """Validate that the prerequisite graph has no missing references and no cycles.
    
    Raises:
        MissingReferenceError: if an item references an unknown prerequisite.
        CycleError: if a circular dependency is detected.
    """
    item_codes: Set[str] = set()
    for it in items:
        code = it.get("item_code") or str(it.get("id", ""))
        if code:
            item_codes.add(code)

    # 1. Missing reference check
    adj: Dict[str, List[str]] = {}
    for it in items:
        code = it.get("item_code") or str(it.get("id", ""))
        if not code:
            continue
        prereqs = it.get("prerequisites") or []
        for p in prereqs:
            if p not in item_codes:
                raise MissingReferenceError(
                    f"Item '{code}' references non-existent prerequisite '{p}'."
                )
        adj[code] = list(prereqs)

    # 2. Cycle detection using 3-color DFS (0=unvisited, 1=visiting, 2=visited)
    visited: Dict[str, int] = {k: 0 for k in adj}

    def dfs(node: str, path: List[str]) -> None:
        visited[node] = 1
        path.append(node)
        for neighbor in adj.get(node, []):
            if visited.get(neighbor) == 1:
                cycle_str = " -> ".join(path + [neighbor])
                raise CycleError(f"Circular dependency detected: {cycle_str}")
            if visited.get(neighbor) == 0:
                dfs(neighbor, path)
        path.pop()
        visited[node] = 2

    for node in adj:
        if visited[node] == 0:
            dfs(node, [])


# ==============================================================================
# 2. PRIORITY ORDERING
# ==============================================================================

def compute_item_skill_gap(
    item: Dict[str, Any],
    tested_skill_levels: Optional[Dict[str, float]] = None,
) -> float:
    """Calculate skill gap based on tested skill levels ONLY.
    
    Declared skills do not count.
    Target level:
      difficulty 1 -> 1.0 (beginner)
      difficulty 2 -> 2.0 (intermediate)
      difficulty 3 -> 3.0 (advanced)
    If tested level > target level and difficulty == 1, the beginner item is downweighted.
    """
    if tested_skill_levels is None:
        tested_skill_levels = {}

    diff = int(item.get("difficulty", 1))
    target_level = float(diff)  # 1.0, 2.0, or 3.0

    skill_key = item.get("skill_slug") or item.get("skill_id")
    tested_level = 0.0
    if skill_key:
        tested_level = float(tested_skill_levels.get(str(skill_key), 0.0))

    gap = target_level - tested_level

    # If tested level is higher than a beginner item, downweight it significantly
    if tested_level >= 2.0 and diff == 1:
        return -5.0

    return max(-5.0, gap)


def order_items_for_scheduling(
    items: List[Dict[str, Any]],
    tested_skill_levels: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Topologically sort items while ordering available candidates by:
    1. Not optional (required items before optional items).
    2. Skill gap descending (largest deficiencies first).
    3. Difficulty ascending (easier concepts before harder within same gap).
    4. Sequence order / code (deterministic tie-break).
    """
    validate_prerequisite_graph(items)

    item_map = {}
    in_degree: Dict[str, int] = {}
    dependents: Dict[str, List[str]] = {}

    for it in items:
        code = it.get("item_code") or str(it.get("id", ""))
        item_map[code] = it
        prereqs = it.get("prerequisites") or []
        in_degree[code] = len(prereqs)
        for p in prereqs:
            dependents.setdefault(p, []).append(code)

    # Calculate gap score for each item
    gap_scores = {code: compute_item_skill_gap(it, tested_skill_levels) for code, it in item_map.items()}

    def candidate_sort_key(code: str) -> Tuple[bool, float, int, int, str]:
        it = item_map[code]
        is_optional = bool(it.get("optional", False))
        gap = gap_scores[code]
        difficulty = int(it.get("difficulty", 1))
        seq = int(it.get("sequence_order", 0))
        # (optional last, highest gap first, lowest diff first, seq order, code)
        return (is_optional, -gap, difficulty, seq, code)

    # Initial available items (in-degree == 0)
    ready = [code for code, deg in in_degree.items() if deg == 0]
    result: List[Dict[str, Any]] = []

    while ready:
        ready.sort(key=candidate_sort_key)
        best_code = ready.pop(0)
        result.append(item_map[best_code])

        for dep in dependents.get(best_code, []):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                ready.append(dep)

    return result


# ==============================================================================
# 3. WEEKLY CAPACITY SCHEDULING WITH 15% BUFFER
# ==============================================================================

def schedule_roadmap_items(
    items: List[Dict[str, Any]],
    hours_per_week: float,
    start_date: datetime,
    timezone_str: str = "UTC",
    tested_skill_levels: Optional[Dict[str, float]] = None,
    exam_cycles: Optional[List[Dict[str, Any]]] = None,
    max_weeks: int = 52,
) -> Dict[str, Any]:
    """Schedule items into discrete weeks respecting weekly capacity with a 15% buffer.
    
    Rules:
    - Usable minutes per week = round(hours_per_week * 60 * (1 - 0.15)).
    - Never schedule more than usable minutes in any week.
    - If hours_per_week == 0, all items go to backlog.
    - Items exceeding max_weeks go to backlog.
    """
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = timezone.utc

    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=tz)
    else:
        start_date = start_date.astimezone(tz)

    total_weekly_minutes = int(round(hours_per_week * 60.0))
    usable_weekly_minutes = int(round(total_weekly_minutes * (1.0 - BUFFER_PERCENTAGE)))

    ordered = order_items_for_scheduling(items, tested_skill_levels)

    if usable_weekly_minutes <= 0:
        # Edge case: zero hours per week -> everything into backlog
        backlog = []
        for it in ordered:
            item_copy = dict(it)
            item_copy["scheduled_week"] = None
            item_copy["scheduled_date"] = None
            item_copy["status"] = item_copy.get("status", "todo")
            backlog.append(item_copy)
        return {
            "scheduled_items": [],
            "backlog_items": backlog,
            "total_weeks": 0,
            "weekly_usable_minutes": 0,
            "buffer_percentage": 15,
        }

    scheduled_items: List[Dict[str, Any]] = []
    backlog_items: List[Dict[str, Any]] = []

    current_week = 1
    current_week_used_minutes = 0

    for it in ordered:
        est_min = int(it.get("estimated_minutes", 60))
        item_copy = dict(it)

        # Check if item fits in current week
        if current_week_used_minutes + est_min <= usable_weekly_minutes:
            item_copy["scheduled_week"] = current_week
            week_start_dt = start_date + timedelta(weeks=current_week - 1)
            item_copy["scheduled_date"] = week_start_dt
            scheduled_items.append(item_copy)
            current_week_used_minutes += est_min
        else:
            # Move to next week
            current_week += 1
            if current_week > max_weeks:
                # Exceeds planning horizon -> overflow to backlog
                item_copy["scheduled_week"] = None
                item_copy["scheduled_date"] = None
                backlog_items.append(item_copy)
            else:
                item_copy["scheduled_week"] = current_week
                week_start_dt = start_date + timedelta(weeks=current_week - 1)
                item_copy["scheduled_date"] = week_start_dt
                scheduled_items.append(item_copy)
                current_week_used_minutes = est_min

    total_scheduled_weeks = max([it["scheduled_week"] for it in scheduled_items], default=0)

    return {
        "scheduled_items": scheduled_items,
        "backlog_items": backlog_items,
        "total_weeks": total_scheduled_weeks,
        "weekly_usable_minutes": usable_weekly_minutes,
        "buffer_percentage": 15,
    }


# ==============================================================================
# 4. REPLANNING ALGORITHM
# ==============================================================================

def replan_roadmap_schedule(
    existing_items: List[Dict[str, Any]],
    replan_date: datetime,
    hours_per_week: float,
    timezone_str: str = "UTC",
    tested_skill_levels: Optional[Dict[str, float]] = None,
    exam_cycles: Optional[List[Dict[str, Any]]] = None,
    max_weeks: int = 52,
) -> Dict[str, Any]:
    """Replan remaining incomplete items starting from today / replan_date.
    
    Rules:
    - Completed ("done") and "skipped" items are left completely UNTOUCHED.
    - Remaining items ("todo", "in_progress") are rescheduled from replan_date (Week 1 of remaining).
    """
    done_or_skipped = [it for it in existing_items if it.get("status") in ("done", "skipped")]
    remaining = [it for it in existing_items if it.get("status") not in ("done", "skipped")]

    # Re-schedule remaining items
    replan_result = schedule_roadmap_items(
        items=remaining,
        hours_per_week=hours_per_week,
        start_date=replan_date,
        timezone_str=timezone_str,
        tested_skill_levels=tested_skill_levels,
        exam_cycles=exam_cycles,
        max_weeks=max_weeks,
    )

    all_items = done_or_skipped + replan_result["scheduled_items"]

    return {
        "all_items": all_items,
        "preserved_count": len(done_or_skipped),
        "rescheduled_count": len(replan_result["scheduled_items"]),
        "backlog_items": replan_result["backlog_items"],
        "total_weeks": replan_result["total_weeks"],
        "summary": {
            "replan_date": replan_date.isoformat(),
            "hours_per_week": hours_per_week,
            "preserved_done_or_skipped": len(done_or_skipped),
            "rescheduled_active": len(replan_result["scheduled_items"]),
            "backlog_count": len(replan_result["backlog_items"]),
        },
    }


# ==============================================================================
# 5. STATUS TRANSITION STATE MACHINE
# ==============================================================================

ALLOWED_TRANSITIONS = {
    "todo": {"todo", "in_progress", "done", "skipped"},
    "in_progress": {"in_progress", "todo", "done", "skipped"},
    "skipped": {"skipped", "todo", "in_progress"},
    "done": {"done"},  # done is final unless force_undo=True
}


def validate_status_transition(
    current_status: str,
    new_status: str,
    force_undo: bool = False,
) -> None:
    """Validate status transition state machine.
    
    Raises:
        ValueError: if the transition is illegal or done is modified without force_undo.
    """
    valid_statuses = {"todo", "in_progress", "done", "skipped"}
    if current_status not in valid_statuses:
        raise ValueError(f"Unknown current status: '{current_status}'.")
    if new_status not in valid_statuses:
        raise ValueError(f"Unknown target status: '{new_status}'.")

    # Idempotent same-status check
    if current_status == new_status:
        return

    # Done is final unless explicitly undone
    if current_status == "done":
        if not force_undo:
            raise ValueError("Completed item ('done') is final and cannot be modified unless explicitly undone.")
        return

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValueError(f"Invalid status transition from '{current_status}' to '{new_status}'.")
