from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest

from app.models.roadmap import (
    RoadmapItem,
    TemplateItem,
)
from app.services.roadmap_engine import (
    CycleError,
    MissingReferenceError,
    order_items_for_scheduling,
    replan_roadmap_schedule,
    schedule_roadmap_items,
    validate_prerequisite_graph,
    validate_status_transition,
)


def _sample_items():
    return [
        {
            "item_code": "p1",
            "title": "Arrays Foundations",
            "type": "problem",
            "estimated_minutes": 60,
            "difficulty": 1,
            "topic": "Arrays",
            "skill_slug": "dsa",
            "prerequisites": [],
            "optional": False,
        },
        {
            "item_code": "p2",
            "title": "Binary Search",
            "type": "problem",
            "estimated_minutes": 60,
            "difficulty": 1,
            "topic": "Binary Search",
            "skill_slug": "dsa",
            "prerequisites": ["p1"],
            "optional": False,
        },
        {
            "item_code": "p3",
            "title": "Two Pointers Trapping Rain Water",
            "type": "problem",
            "estimated_minutes": 120,
            "difficulty": 3,
            "topic": "Two Pointers",
            "skill_slug": "dsa",
            "prerequisites": ["p1"],
            "optional": False,
        },
        {
            "item_code": "proj1",
            "title": "Optional Capstone Project",
            "type": "project",
            "estimated_minutes": 240,
            "difficulty": 2,
            "topic": "Web Systems",
            "skill_slug": "python",
            "prerequisites": ["p2"],
            "optional": True,
        },
    ]


# ==============================================================================
# 1. GRAPH VALIDATION TESTS
# ==============================================================================

def test_prerequisite_graph_valid():
    items = _sample_items()
    validate_prerequisite_graph(items)  # Should not raise


def test_prerequisite_graph_missing_reference():
    items = [
        {"item_code": "a", "prerequisites": ["non_existent_item"]},
    ]
    with pytest.raises(MissingReferenceError) as exc_info:
        validate_prerequisite_graph(items)
    assert "non_existent_item" in str(exc_info.value)


def test_prerequisite_graph_cycle_detection():
    # A -> B -> C -> A
    items = [
        {"item_code": "a", "prerequisites": ["c"]},
        {"item_code": "b", "prerequisites": ["a"]},
        {"item_code": "c", "prerequisites": ["b"]},
    ]
    with pytest.raises(CycleError) as exc_info:
        validate_prerequisite_graph(items)
    assert "Circular dependency detected" in str(exc_info.value)


def test_prerequisite_graph_self_dependency():
    items = [
        {"item_code": "a", "prerequisites": ["a"]},
    ]
    with pytest.raises(CycleError):
        validate_prerequisite_graph(items)


# ==============================================================================
# 2. PRIORITY ORDERING & TESTED SKILL GAP TESTS
# ==============================================================================

def test_prerequisites_always_before_dependents():
    items = _sample_items()
    ordered = order_items_for_scheduling(items)
    codes = [it["item_code"] for it in ordered]

    # p1 must appear before p2, p3, and proj1
    assert codes.index("p1") < codes.index("p2")
    assert codes.index("p1") < codes.index("p3")
    assert codes.index("p2") < codes.index("proj1")


def test_optional_items_scheduled_last():
    items = _sample_items()
    ordered = order_items_for_scheduling(items)
    codes = [it["item_code"] for it in ordered]
    # proj1 is optional, so it must be last
    assert codes[-1] == "proj1"


def test_tested_skill_higher_downweights_beginner_items():
    # User tested as advanced in DSA (level 3.0)
    tested_levels = {"dsa": 3.0}
    items = [
        {
            "item_code": "dsa_beg",
            "title": "Beginner DSA",
            "estimated_minutes": 60,
            "difficulty": 1,
            "skill_slug": "dsa",
            "prerequisites": [],
            "optional": False,
        },
        {
            "item_code": "dsa_adv",
            "title": "Advanced DSA",
            "estimated_minutes": 60,
            "difficulty": 3,
            "skill_slug": "dsa",
            "prerequisites": [],
            "optional": False,
        },
    ]
    ordered = order_items_for_scheduling(items, tested_skill_levels=tested_levels)
    codes = [it["item_code"] for it in ordered]
    # Because user already tested at 3.0, the beginner item is downweighted
    assert codes[0] == "dsa_adv"
    assert codes[1] == "dsa_beg"


# ==============================================================================
# 3. WEEKLY CAPACITY SCHEDULING & 15% BUFFER TESTS
# ==============================================================================

def test_buffer_respected_and_no_week_exceeds_available_minutes():
    # 10 hours per week = 600 minutes
    # 15% buffer = 90 minutes -> usable = 510 minutes
    hours_per_week = 10.0
    start_date = datetime(2026, 3, 2, tzinfo=timezone.utc)
    items = [
        {"item_code": f"task_{i}", "estimated_minutes": 200, "difficulty": 1, "prerequisites": [], "optional": False}
        for i in range(1, 6)
    ]
    # 5 items * 200 min = 1000 min total
    # Week 1: 200 + 200 = 400 min (fits in 510, 3rd item would be 600 > 510)
    # Week 2: 200 + 200 = 400 min
    # Week 3: 200 min
    result = schedule_roadmap_items(
        items=items,
        hours_per_week=hours_per_week,
        start_date=start_date,
    )

    assert result["weekly_usable_minutes"] == int(round(600 * 0.85))  # 510
    assert result["buffer_percentage"] == 15
    scheduled = result["scheduled_items"]
    assert len(scheduled) == 5

    # Group minutes by scheduled_week
    week_minutes = {}
    for it in scheduled:
        w = it["scheduled_week"]
        week_minutes[w] = week_minutes.get(w, 0) + it["estimated_minutes"]

    for w, total_min in week_minutes.items():
        assert total_min <= result["weekly_usable_minutes"], f"Week {w} exceeded usable minutes!"


def test_empty_hours_edge_case_all_to_backlog():
    # 0 hours per week -> all items to backlog
    start_date = datetime(2026, 3, 2, tzinfo=timezone.utc)
    items = _sample_items()
    result = schedule_roadmap_items(
        items=items,
        hours_per_week=0.0,
        start_date=start_date,
    )
    assert result["weekly_usable_minutes"] == 0
    assert len(result["scheduled_items"]) == 0
    assert len(result["backlog_items"]) == len(items)


def test_timezone_week_boundaries():
    start_date_utc = datetime(2026, 3, 2, 0, 0, 0, tzinfo=timezone.utc)
    items = [
        {"item_code": "t1", "estimated_minutes": 100, "difficulty": 1, "prerequisites": [], "optional": False},
        {"item_code": "t2", "estimated_minutes": 100, "difficulty": 1, "prerequisites": [], "optional": False},
    ]
    result = schedule_roadmap_items(
        items=items,
        hours_per_week=2.0,  # 120 * 0.85 = 102 min/week -> each item takes 1 week
        start_date=start_date_utc,
        timezone_str="Asia/Kolkata",
    )
    scheduled = result["scheduled_items"]
    assert scheduled[0]["scheduled_week"] == 1
    assert scheduled[1]["scheduled_week"] == 2
    # Week 2 date should be exactly 7 days after Week 1
    dt1 = scheduled[0]["scheduled_date"]
    dt2 = scheduled[1]["scheduled_date"]
    assert dt2 - dt1 == timedelta(weeks=1)


# ==============================================================================
# 4. REPLANNING TESTS
# ==============================================================================

def test_replan_preserves_completed_and_skipped_items():
    t_past = datetime(2026, 2, 1, tzinfo=timezone.utc)
    t_done = datetime(2026, 2, 3, tzinfo=timezone.utc)
    t_now = datetime(2026, 3, 1, tzinfo=timezone.utc)

    existing_items = [
        {
            "item_code": "done_1",
            "title": "Done Task",
            "status": "done",
            "scheduled_week": 1,
            "scheduled_date": t_past,
            "completed_at": t_done,
            "estimated_minutes": 60,
            "difficulty": 1,
            "prerequisites": [],
        },
        {
            "item_code": "skipped_1",
            "title": "Skipped Task",
            "status": "skipped",
            "scheduled_week": 1,
            "scheduled_date": t_past,
            "completed_at": None,
            "estimated_minutes": 60,
            "difficulty": 1,
            "prerequisites": [],
        },
        {
            "item_code": "todo_1",
            "title": "Pending Task",
            "status": "todo",
            "scheduled_week": 2,
            "scheduled_date": t_past,
            "completed_at": None,
            "estimated_minutes": 120,
            "difficulty": 2,
            "prerequisites": [],
        },
    ]

    replan_res = replan_roadmap_schedule(
        existing_items=existing_items,
        replan_date=t_now,
        hours_per_week=5.0,
    )

    all_items = replan_res["all_items"]
    done_item = next(it for it in all_items if it["item_code"] == "done_1")
    skipped_item = next(it for it in all_items if it["item_code"] == "skipped_1")
    todo_item = next(it for it in all_items if it["item_code"] == "todo_1")

    # Completed & skipped preserved exactly
    assert done_item["status"] == "done"
    assert done_item["completed_at"] == t_done
    assert done_item["scheduled_date"] == t_past

    assert skipped_item["status"] == "skipped"
    assert skipped_item["scheduled_date"] == t_past

    # Todo item rescheduled from t_now (replan_date)
    assert todo_item["status"] == "todo"
    assert todo_item["scheduled_week"] == 1
    assert todo_item["scheduled_date"] == t_now


# ==============================================================================
# 5. TEMPLATE EDIT INDEPENDENCE TEST
# ==============================================================================

def test_template_edit_does_not_alter_existing_roadmap():
    # Create template
    tmpl_id = uuid4()
    item_id = uuid4()
    tmpl_item = TemplateItem(
        id=item_id,
        template_id=tmpl_id,
        item_code="code_orig",
        type="problem",
        title="Original Template Problem",
        estimated_minutes=60,
        difficulty=1,
        topic="Arrays",
        prerequisites=[],
        optional=False,
        status="verified",
    )

    # Cloned user roadmap item
    user_roadmap_id = uuid4()
    roadmap_item = RoadmapItem(
        id=uuid4(),
        roadmap_id=user_roadmap_id,
        item_code=tmpl_item.item_code,
        type=tmpl_item.type,
        title=tmpl_item.title,
        estimated_minutes=tmpl_item.estimated_minutes,
        difficulty=tmpl_item.difficulty,
        topic=tmpl_item.topic,
        prerequisites=list(tmpl_item.prerequisites),
        optional=tmpl_item.optional,
        status="in_progress",
        scheduled_week=1,
    )

    # Now author edits template
    tmpl_item.title = "Modified Template Problem - Renamed!"
    tmpl_item.estimated_minutes = 180
    tmpl_item.difficulty = 3

    # Existing user roadmap item remains unchanged
    assert roadmap_item.title == "Original Template Problem"
    assert roadmap_item.estimated_minutes == 60
    assert roadmap_item.difficulty == 1
    assert roadmap_item.status == "in_progress"


# ==============================================================================
# 6. STATUS TRANSITION STATE MACHINE TESTS
# ==============================================================================

def test_valid_status_transitions():
    validate_status_transition("todo", "in_progress")
    validate_status_transition("todo", "done")
    validate_status_transition("todo", "skipped")
    validate_status_transition("in_progress", "done")
    validate_status_transition("in_progress", "skipped")
    validate_status_transition("skipped", "todo")
    # Idempotent
    validate_status_transition("todo", "todo")
    validate_status_transition("done", "done")


def test_invalid_status_transitions():
    # Done is final unless force_undo=True
    with pytest.raises(ValueError) as exc1:
        validate_status_transition("done", "todo", force_undo=False)
    assert "is final" in str(exc1.value).lower()

    with pytest.raises(ValueError) as exc2:
        validate_status_transition("done", "in_progress", force_undo=False)
    assert "is final" in str(exc2.value).lower()

    # Allowed with force_undo
    validate_status_transition("done", "todo", force_undo=True)
    validate_status_transition("done", "in_progress", force_undo=True)

    # Unknown status
    with pytest.raises(ValueError) as exc3:
        validate_status_transition("todo", "non_existent_status")
    assert "Unknown target status" in str(exc3.value)
