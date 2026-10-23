"""Recommendation Engine.

Pure, deterministic business logic for:
1. Expiry and 90-day staleness filtering.
2. User constraint filtering (budget, location, hours available, eligibility, user action states).
3. Ranking by career match, skill gaps, level fit, and cost with deterministic tie-break.
4. Deterministic, code-grounded generation of `why_it_fits`.
5. Non-personalized fallback path for users without assessment or skill evidence.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


STALENESS_DAYS_THRESHOLD = 90

BUDGET_CAPS = {
    "low": 50000,       # Up to 50k INR / free
    "medium": 250000,   # Up to 2.5L INR
    "high": 10000000,   # High / no cap
}


def is_item_active_and_verified(
    item: Dict[str, Any],
    now: datetime,
    allow_drafts: bool = False,
) -> bool:
    """Check if an item is verified, not stale (> 90 days), and not expired."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Verification check
    if not allow_drafts:
        if item.get("status") != "verified":
            return False
        # 90-day staleness check
        last_verified = item.get("last_verified_at")
        if not last_verified:
            return False
        if last_verified.tzinfo is None:
            last_verified = last_verified.replace(tzinfo=timezone.utc)
        if (now - last_verified).days > STALENESS_DAYS_THRESHOLD:
            return False

    # 2. Expiry check
    expires_at = item.get("expires_at")
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            return False

    # 3. Application deadline check
    deadline = item.get("application_deadline")
    if deadline:
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= now:
            return False

    return True


def matches_budget(item: Dict[str, Any], budget_level: Optional[str] = None, max_budget_inr: Optional[int] = None) -> bool:
    """Check if item cost fits user budget constraint."""
    cost = item.get("cost_inr")
    if cost is None or cost == 0:
        return True  # Free or unstated cost fits budget

    if max_budget_inr is not None and cost > max_budget_inr:
        return False

    if budget_level:
        cap = BUDGET_CAPS.get(budget_level.lower())
        if cap is not None and cost > cap:
            return False

    return True


def matches_location(item: Dict[str, Any], user_location: Optional[str] = None) -> bool:
    """Check if item location fits user preference."""
    if not user_location:
        return True

    mode = str(item.get("mode") or "").lower()
    if mode == "online":
        return True

    user_loc_clean = user_location.strip().lower()
    if user_loc_clean == "remote":
        return mode in ("online", "remote")

    # Check location JSONB or locations list
    item_loc = item.get("location")
    if isinstance(item_loc, dict):
        city = str(item_loc.get("city", "")).lower()
        state = str(item_loc.get("state", "")).lower()
        country = str(item_loc.get("country", "")).lower()
        if user_loc_clean in (city, state, country) or city in user_loc_clean:
            return True

    item_locations = item.get("locations") or []
    if isinstance(item_locations, list):
        for loc in item_locations:
            loc_clean = str(loc).strip().lower()
            if user_loc_clean in loc_clean or loc_clean in user_loc_clean:
                return True

    return False


def matches_hours(item: Dict[str, Any], hours_available: Optional[int] = None) -> bool:
    """Check if weekly commitment fits user hours available."""
    if hours_available is None or hours_available <= 0:
        return True

    # If item has estimated hours per week or duration
    item_weekly_hours = item.get("weekly_hours") or item.get("hours_per_week")
    if item_weekly_hours and int(item_weekly_hours) > hours_available:
        return False

    return True


def filter_recommendation_candidates(
    items: List[Dict[str, Any]],
    now: datetime,
    budget_level: Optional[str] = None,
    max_budget_inr: Optional[int] = None,
    user_location: Optional[str] = None,
    hours_available: Optional[int] = None,
    user_actions: Optional[Dict[Tuple[str, str], str]] = None,
    include_dismissed: bool = False,
    saved_only: bool = False,
    allow_drafts: bool = False,
) -> List[Dict[str, Any]]:
    """Filter candidate items against verification, staleness, expiry, user budget, location, hours, and action states."""
    if user_actions is None:
        user_actions = {}

    filtered = []
    for it in items:
        # 1. Verification, staleness, expiry
        if not is_item_active_and_verified(it, now=now, allow_drafts=allow_drafts):
            continue

        # 2. User interaction state filter
        action_key = (it.get("item_type", ""), str(it.get("id", "")))
        action_state = user_actions.get(action_key, "none")
        it["user_state"] = action_state

        if saved_only and action_state != "saved":
            continue

        if not include_dismissed and action_state == "dismissed":
            continue

        if action_state == "done":
            continue  # Already accomplished

        # 3. Constraint filters
        if not matches_budget(it, budget_level=budget_level, max_budget_inr=max_budget_inr):
            continue

        if not matches_location(it, user_location=user_location):
            continue

        if not matches_hours(it, hours_available=hours_available):
            continue

        filtered.append(it)

    return filtered


# ==============================================================================
# RANKING AND DETERMINISTIC WHY_IT_FITS GENERATION
# ==============================================================================

def score_and_rank_item(
    item: Dict[str, Any],
    target_career_title: Optional[str] = None,
    target_career_id: Optional[str] = None,
    user_skill_levels: Optional[Dict[str, float]] = None,
    user_budget_level: Optional[str] = None,
    user_location: Optional[str] = None,
    hours_available: Optional[int] = None,
) -> Tuple[int, str]:
    """Calculate matching score (0-100) and build deterministic why_it_fits explanation."""
    reasons = []
    score = 40  # Base catalog relevance score

    # 1. Career match
    item_career_ids = set(str(cid) for cid in (item.get("career_ids") or []))
    if target_career_id and str(target_career_id) in item_career_ids:
        score += 30
        if target_career_title:
            reasons.append(f"Directly prepares for {target_career_title}")
    elif target_career_title:
        domain = item.get("domain") or item.get("topic") or ""
        if domain.lower() in target_career_title.lower() or target_career_title.lower() in domain.lower():
            score += 20
            reasons.append(f"Aligns with your {target_career_title} pathway")

    # 2. Skill gap match
    item_skills = item.get("skills") or []
    if user_skill_levels is not None and item_skills:
        has_gap = False
        for sk in item_skills:
            slug = sk.get("slug") or sk.get("name", "").lower()
            lvl = user_skill_levels.get(slug, 0.0)
            if lvl < 2.5:  # Tested gap exists
                has_gap = True
                reasons.append(f"Strengthens tested skill gap in {sk.get('name', slug.title())}")
                score += 15
                break
        if not has_gap:
            score += 5

    # 3. Location / Mode match
    mode = str(item.get("mode") or "").lower()
    if mode == "online":
        reasons.append("Online self-paced access")
        score += 5
    elif user_location and matches_location(item, user_location):
        reasons.append(f"Available locally in {user_location.title()}")
        score += 10

    # 4. Cost / Budget fit
    cost = item.get("cost_inr")
    if cost == 0 and item.get("status") == "verified":
        reasons.append("Zero tuition (Free verified resource)")
        score += 10
    elif cost is not None:
        reasons.append(f"Cost fits your {user_budget_level or 'budget'} profile")
        score += 5

    # 5. Hours fit
    if hours_available and matches_hours(item, hours_available):
        reasons.append(f"Fits within {hours_available} hrs/week bandwidth")

    why_it_fits = "; ".join(reasons) if reasons else "Recommended foundational opportunity for your career path"
    final_score = max(0, min(100, score))
    return final_score, why_it_fits


def rank_recommendations(
    items: List[Dict[str, Any]],
    target_career_title: Optional[str] = None,
    target_career_id: Optional[str] = None,
    user_skill_levels: Optional[Dict[str, float]] = None,
    user_budget_level: Optional[str] = None,
    user_location: Optional[str] = None,
    hours_available: Optional[int] = None,
    is_personalised: bool = True,
) -> List[Dict[str, Any]]:
    """Score, generate why_it_fits, and rank items deterministically.
    
    Tie-break: score descending, then title ascending, then ID ascending.
    """
    scored_items = []
    for it in items:
        item_copy = dict(it)
        if is_personalised:
            score, why_text = score_and_rank_item(
                item=item_copy,
                target_career_title=target_career_title,
                target_career_id=target_career_id,
                user_skill_levels=user_skill_levels,
                user_budget_level=user_budget_level,
                user_location=user_location,
                hours_available=hours_available,
            )
        else:
            score = 50
            career_name = target_career_title or "your career"
            why_text = f"Standard foundational recommendation for {career_name}"

        item_copy["match_score"] = score
        item_copy["why_it_fits"] = why_text
        scored_items.append(item_copy)

    # Deterministic tie-break: (-score, title, str(id))
    scored_items.sort(
        key=lambda x: (
            -int(x.get("match_score", 0)),
            str(x.get("title", "")).lower(),
            str(x.get("id", "")),
        )
    )
    return scored_items
