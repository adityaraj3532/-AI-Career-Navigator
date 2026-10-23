"""Skill Tracker Engine.

Pure, deterministic business logic for computing:
1. Effective skill level and confidence from weighted evidence (source weights, recency decay, source caps).
2. Subtopic strengths and weak subtopics.
3. Historical trend over time (strictly None if < 2 evidence points).
4. Deterministic fallback report generation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


SKILL_TRACKER_WEIGHTS_V1 = {
    "version": 1,
    "source_weights": {
        "test": 1.0,
        "project": 0.6,
        "roadmap": 0.35,
        "declared": 0.15,
    },
    "source_caps": {
        "declared": 1.0,    # Max "beginner"
        "roadmap": 2.0,     # Max "intermediate"
        "project": 3.0,     # Max "advanced"
        "test": 3.0,        # Max "advanced"
    },
    "recency_half_life_days": 30.0,
    "level_values": {
        "beginner": 1.0,
        "intermediate": 2.0,
        "advanced": 3.0,
    },
    "level_thresholds": {
        "advanced": 2.5,
        "intermediate": 1.6,
    },
    "confidence_thresholds": {
        "high_min_weight": 1.8,
        "medium_min_weight": 0.8,
    },
    "subtopic_thresholds": {
        "strength_min": 70,  # >= 70%
        "weakness_max": 59,  # < 60%
    },
}


def level_to_value(level_str: str) -> float:
    """Convert a discrete level string to numeric value."""
    return SKILL_TRACKER_WEIGHTS_V1["level_values"].get(level_str.lower(), 1.0)


def value_to_level(val: float) -> str:
    """Convert numeric value to discrete level string."""
    thresh = SKILL_TRACKER_WEIGHTS_V1["level_thresholds"]
    if val >= thresh["advanced"]:
        return "advanced"
    if val >= thresh["intermediate"]:
        return "intermediate"
    return "beginner"


def score_to_level_value(score: int) -> float:
    """Convert a percentage score (0-100) to numeric level value."""
    if score >= 80:
        return 3.0  # advanced
    elif score >= 50:
        return 2.0  # intermediate
    return 1.0  # beginner


def compute_evidence_weight(
    source_type: str,
    created_at: datetime,
    now: Optional[datetime] = None,
) -> float:
    """Compute recency-decayed weight for an evidence item."""
    base_weight = SKILL_TRACKER_WEIGHTS_V1["source_weights"].get(source_type, 0.1)
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Ensure UTC timezone awareness
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    delta_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    half_life = SKILL_TRACKER_WEIGHTS_V1["recency_half_life_days"]
    recency_factor = 0.5 ** (delta_days / half_life)
    return base_weight * recency_factor


def compute_skill_level_and_confidence(
    evidence_items: List[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> Tuple[str, str, float]:
    """Calculate aggregate (current_level, confidence, numeric_level) from evidence items.

    Caps:
    - Declared signals cannot exceed beginner (1.0).
    - Roadmap signals cannot exceed intermediate (2.0).
    - If user has NO test evidence, overall score cannot exceed the maximum allowed
      by the present non-test sources.
    - Confidence requires >= 1.8 total effective weight AND at least 1 test for 'high'.
    """
    if not evidence_items:
        return ("beginner", "low", 1.0)

    total_weight = 0.0
    weighted_sum = 0.0
    has_test = False
    max_allowed_source_cap = 1.0

    source_caps = SKILL_TRACKER_WEIGHTS_V1["source_caps"]

    for item in evidence_items:
        src = item.get("source_type", "declared")
        created_at = item.get("created_at") or datetime.now(timezone.utc)
        weight = compute_evidence_weight(src, created_at, now=now)

        if src == "test":
            has_test = True

        src_cap = source_caps.get(src, 1.0)
        if src_cap > max_allowed_source_cap:
            max_allowed_source_cap = src_cap

        # Determine level signal value for this item
        if item.get("level_signal"):
            raw_val = level_to_value(item["level_signal"])
        elif item.get("score") is not None:
            raw_val = score_to_level_value(int(item["score"]))
        else:
            raw_val = 1.0

        # Cap individual item by source cap
        capped_val = min(raw_val, src_cap)

        weighted_sum += weight * capped_val
        total_weight += weight

    if total_weight <= 0:
        return ("beginner", "low", 1.0)

    raw_overall_val = weighted_sum / total_weight

    # Cap overall level if no test evidence exists
    if not has_test:
        effective_val = min(raw_overall_val, max_allowed_source_cap)
    else:
        effective_val = raw_overall_val

    discrete_level = value_to_level(effective_val)

    # Confidence calculation
    conf_thresh = SKILL_TRACKER_WEIGHTS_V1["confidence_thresholds"]
    if total_weight >= conf_thresh["high_min_weight"] and has_test:
        confidence = "high"
    elif total_weight >= conf_thresh["medium_min_weight"]:
        confidence = "medium"
    else:
        confidence = "low"

    return (discrete_level, confidence, round(effective_val, 2))


def analyze_subtopics(evidence_items: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Analyze subtopic scores across evidence to identify strengths (>= 70%) and weak subtopics (< 60%)."""
    subtopic_totals: Dict[str, List[float]] = {}

    for item in evidence_items:
        sub_scores = item.get("subtopic_scores") or {}
        for sub, score in sub_scores.items():
            if isinstance(score, (int, float)):
                subtopic_totals.setdefault(sub, []).append(float(score))

    strengths = []
    weaknesses = []

    for sub, scores in subtopic_totals.items():
        avg_score = sum(scores) / len(scores)
        if avg_score >= SKILL_TRACKER_WEIGHTS_V1["subtopic_thresholds"]["strength_min"]:
            strengths.append(sub)
        elif avg_score <= SKILL_TRACKER_WEIGHTS_V1["subtopic_thresholds"]["weakness_max"]:
            weaknesses.append(sub)

    strengths.sort()
    weaknesses.sort()
    return (strengths, weaknesses)


def compute_trend_over_time(evidence_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Derive historical progression trend.
    
    Invariant: Returns None if len(evidence_items) < 2.
    """
    if len(evidence_items) < 2:
        return None

    # Sort evidence items chronologically ascending
    sorted_items = sorted(
        evidence_items,
        key=lambda x: x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
    )

    history = []
    cumulative_items: List[Dict[str, Any]] = []

    for item in sorted_items:
        cumulative_items.append(item)
        lvl, _, num_val = compute_skill_level_and_confidence(cumulative_items, now=item.get("created_at"))
        created_at_dt = item.get("created_at")
        date_str = created_at_dt.isoformat() if hasattr(created_at_dt, "isoformat") else str(created_at_dt)
        history.append({
            "date": date_str,
            "source_type": item.get("source_type"),
            "level_signal": item.get("level_signal"),
            "score": item.get("score"),
            "computed_level": lvl,
            "level_value": num_val,
        })

    first_val = history[0]["level_value"]
    last_val = history[-1]["level_value"]
    diff = last_val - first_val

    if diff > 0.25:
        direction = "improving"
    elif diff < -0.25:
        direction = "declining"
    else:
        direction = "stable"

    return {
        "direction": direction,
        "start_level": history[0]["computed_level"],
        "current_level": history[-1]["computed_level"],
        "history": history,
    }


def generate_fallback_report_text(
    skill_name: str,
    level: str,
    confidence: str,
    strengths: List[str],
    weaknesses: List[str],
    evidence_count: int,
) -> str:
    """Generate a clean, deterministic summary text template."""
    strengths_txt = ", ".join(strengths) if strengths else "Foundational concepts"
    weaknesses_txt = ", ".join(weaknesses) if weaknesses else "None flagged yet"

    return (
        f"Skill Report for {skill_name}: Currently assessed at '{level.title()}' level "
        f"with {confidence} confidence based on {evidence_count} evidence item(s). "
        f"Demonstrated strengths include: {strengths_txt}. "
        f"Priority growth areas: {weaknesses_txt}. "
        f"Complete targeted practice and assessments to verify higher proficiency."
    )
