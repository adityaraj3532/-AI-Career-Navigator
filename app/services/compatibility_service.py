import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.assessment import AssessmentResult
from app.models.career import Career, UserCareerCompatibilitySnapshot
from app.models.profile import StudentProfile
from app.models.user import User
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.career_repository import CareerRepository
from app.repositories.compatibility_repository import CompatibilityRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.shortlist_repository import ShortlistRepository
from app.schemas.career import SalaryRangesSchema
from app.schemas.compatibility import (
    CompareCareerItem,
    CompareResponse,
    CompatibilityHistoryResponse,
    CompatibilitySnapshotResponse,
    FactorBreakdownItem,
    ShortlistActionResponse,
    ShortlistItemResponse,
    ShortlistListResponse,
)
from app.services.scoring_service import calculate_career_similarity

COMPATIBILITY_WEIGHTS_V1: Dict[str, Any] = {
    "version": 1,
    "weights": {
        "interest_fit": 30,
        "skills": 25,
        "subjects": 20,
        "hours": 15,
        "budget": 10,
    },
}

ALL_FACTORS: Tuple[str, ...] = ("interest_fit", "skills", "subjects", "hours", "budget")

SKILL_LEVEL_WEIGHTS: Dict[str, float] = {
    "beginner": 0.5,
    "intermediate": 0.75,
    "advanced": 0.9,
    "expert": 1.0,
}

DOMAIN_SUBJECT_MAPPING: Dict[str, set] = {
    "STEM_TECH": {
        "mathematics", "computer science", "physics", "statistics", "information technology",
        "coding", "programming", "logic", "ai", "machine learning", "data structures",
    },
    "HEALTHCARE": {
        "biology", "chemistry", "physics", "biotechnology", "health science",
        "life sciences", "anatomy", "physiology", "medicine",
    },
    "FINANCE_COMMERCE": {
        "accountancy", "mathematics", "economics", "business studies", "commerce",
        "statistics", "finance", "taxation", "auditing",
    },
    "CIVIL_HUMANITIES": {
        "history", "political science", "economics", "geography", "sociology",
        "public administration", "english", "law", "philosophy", "psychology",
    },
    "DESIGN_ARTS": {
        "design", "art", "psychology", "computer science", "visual arts",
        "multimedia", "human-computer interaction", "graphic design",
    },
    "MECHANICAL_ENG": {
        "physics", "mathematics", "chemistry", "engineering drawing",
        "mechanics", "thermodynamics", "manufacturing",
    },
}


def _normalize_tokens(text: str) -> set:
    tokens = re.findall(r"\b[a-zA-Z0-9+#.]+\b", text.lower())
    return set(tokens)


def _evaluate_interest_fit(
    career: Career,
    assessment_result: Optional[AssessmentResult],
) -> Optional[Tuple[int, str]]:
    if not assessment_result or not assessment_result.dimension_scores:
        return None
    if not career.dimension_weights:
        return None

    sim = calculate_career_similarity(assessment_result.dimension_scores, career.dimension_weights)
    score = int(round(sim * 100.0))
    score = max(0, min(100, score))
    details = f"RIASEC alignment score: {score}% based on your assessment results."
    return score, details


def _evaluate_skills(
    career: Career,
    profile: Optional[StudentProfile],
) -> Optional[Tuple[int, str]]:
    if not profile or not profile.skills or len(profile.skills) == 0:
        return None

    required_skills = career.required_skills or []
    if not required_skills:
        return 100, "No specific required skills listed for this career."

    # Parse profile skills
    user_skills_map: Dict[str, float] = {}
    for s in profile.skills:
        if isinstance(s, dict):
            s_name = str(s.get("name", "")).strip().lower()
            s_lvl = str(s.get("level", "intermediate")).strip().lower()
            lvl_val = SKILL_LEVEL_WEIGHTS.get(s_lvl, 0.75)
        else:
            s_name = str(s).strip().lower()
            lvl_val = 0.75
        if s_name:
            user_skills_map[s_name] = lvl_val

    matched_ratios: List[float] = []
    matched_names: List[str] = []

    for req in required_skills:
        req_name = str(req.get("name", "")).strip().lower()
        req_lvl = str(req.get("level", "intermediate")).strip().lower()
        req_target = SKILL_LEVEL_WEIGHTS.get(req_lvl, 0.75)

        req_tokens = _normalize_tokens(req_name)
        best_match_ratio = 0.0

        for u_name, u_val in user_skills_map.items():
            u_tokens = _normalize_tokens(u_name)
            # Direct match or substring or token intersection
            is_match = (
                u_name == req_name
                or u_name in req_name
                or req_name in u_name
                or (len(req_tokens & u_tokens) > 0)
            )
            if is_match:
                ratio = min(1.0, u_val / req_target)
                if ratio > best_match_ratio:
                    best_match_ratio = ratio

        matched_ratios.append(best_match_ratio)
        if best_match_ratio >= 0.5:
            matched_names.append(req.get("name", ""))

    overall_ratio = sum(matched_ratios) / len(required_skills)
    score = int(round(overall_ratio * 100.0))
    score = max(0, min(100, score))
    details = f"Matched {len(matched_names)} of {len(required_skills)} required skills ({score}%)."
    return score, details


def _evaluate_subjects(
    career: Career,
    profile: Optional[StudentProfile],
) -> Optional[Tuple[int, str]]:
    if not profile or not profile.subjects_of_interest or len(profile.subjects_of_interest) == 0:
        return None

    user_subjects = [s.strip().lower() for s in profile.subjects_of_interest if s.strip()]
    if not user_subjects:
        return None

    # Determine domain relevant subjects
    domain_set = set()
    cluster_lower = (career.cluster or "").lower()
    code_upper = (career.code or "").upper()

    if "technology" in cluster_lower or "engineer" in cluster_lower or "sde" in code_upper or "ai" in code_upper or "data" in code_upper:
        domain_set.update(DOMAIN_SUBJECT_MAPPING["STEM_TECH"])
    if "health" in cluster_lower or "doc" in code_upper or "medical" in cluster_lower:
        domain_set.update(DOMAIN_SUBJECT_MAPPING["HEALTHCARE"])
    if "finance" in cluster_lower or "ca" in code_upper or "account" in cluster_lower or "business" in cluster_lower:
        domain_set.update(DOMAIN_SUBJECT_MAPPING["FINANCE_COMMERCE"])
    if "civil" in code_upper or "government" in cluster_lower or "public" in cluster_lower:
        domain_set.update(DOMAIN_SUBJECT_MAPPING["CIVIL_HUMANITIES"])
    if "design" in cluster_lower or "ui" in code_upper or "creative" in cluster_lower:
        domain_set.update(DOMAIN_SUBJECT_MAPPING["DESIGN_ARTS"])
    if "mechanical" in code_upper:
        domain_set.update(DOMAIN_SUBJECT_MAPPING["MECHANICAL_ENG"])

    # Fallback if domain_set is empty: use career title & overview tokens
    if not domain_set:
        domain_set = _normalize_tokens(career.title) | _normalize_tokens(career.cluster)

    matched_subjects = []
    for s in user_subjects:
        s_tokens = _normalize_tokens(s)
        if s in domain_set or (s_tokens & domain_set):
            matched_subjects.append(s)

    match_count = len(matched_subjects)
    if match_count >= 3:
        score = 100
    elif match_count == 2:
        score = 85
    elif match_count == 1:
        score = 70
    else:
        score = 30

    if matched_subjects:
        details = f"Aligned subjects: {', '.join(matched_subjects)} ({score}%)."
    else:
        details = f"Subjects do not directly align with {career.cluster} pathway ({score}%)."
    return score, details


def _evaluate_hours(
    career: Career,
    profile: Optional[StudentProfile],
) -> Optional[Tuple[int, str]]:
    if not profile or profile.hours_available_per_week is None:
        return None

    user_hours = max(0, profile.hours_available_per_week)
    diff = (career.entrance_difficulty or "moderate").strip().lower()

    if diff == "extreme":
        recommended_hours = 30
    elif diff == "high":
        recommended_hours = 25
    else:
        recommended_hours = 15

    ratio = min(1.0, user_hours / recommended_hours) if recommended_hours > 0 else 1.0
    score = int(round(ratio * 100.0))
    score = max(0, min(100, score))
    details = f"{user_hours} hrs/week available vs {recommended_hours} hrs/week recommended ({score}%)."
    return score, details


def _evaluate_budget(
    career: Career,
    profile: Optional[StudentProfile],
) -> Optional[Tuple[int, str]]:
    if not profile or not profile.budget_level or not profile.budget_level.strip():
        return None

    user_budget = profile.budget_level.strip().lower()
    cluster_lower = (career.cluster or "").lower()
    code_upper = (career.code or "").upper()

    if "health" in cluster_lower or "doc" in code_upper:
        career_req = "high"
    elif "ca" in code_upper or "civil" in code_upper:
        career_req = "low"
    else:
        career_req = "medium"

    budget_scores: Dict[str, Dict[str, int]] = {
        "high": {"low": 100, "medium": 100, "high": 100},
        "medium": {"low": 100, "medium": 100, "high": 75},
        "low": {"low": 100, "medium": 70, "high": 40},
    }
    score = budget_scores.get(user_budget, budget_scores["medium"]).get(career_req, 75)
    details = f"Student budget '{user_budget}' vs career requirement '{career_req}' ({score}%)."
    return score, details


def compute_career_compatibility(
    career: Career,
    assessment_result: Optional[AssessmentResult] = None,
    profile: Optional[StudentProfile] = None,
    weights_config: Optional[Dict[str, Any]] = None,
) -> Tuple[int, int, List[str], Dict[str, Any], List[str], List[str]]:
    """
    Pure scoring function that evaluates transparent 0-100 compatibility.
    - Excludes factors with missing data and re-normalises remaining weights so sum(weights) == 1.0.
    - Never scores missing data as 0.
    - Returns (overall_score, data_completeness, excluded_factors, factor_breakdown, strengths, gaps).
    """
    config = weights_config or COMPATIBILITY_WEIGHTS_V1
    base_weights = config.get("weights", COMPATIBILITY_WEIGHTS_V1["weights"])

    evaluators = {
        "interest_fit": lambda: _evaluate_interest_fit(career, assessment_result),
        "skills": lambda: _evaluate_skills(career, profile),
        "subjects": lambda: _evaluate_subjects(career, profile),
        "hours": lambda: _evaluate_hours(career, profile),
        "budget": lambda: _evaluate_budget(career, profile),
    }

    present_factors: Dict[str, Tuple[int, str]] = {}
    excluded_factors: List[str] = []

    for factor in ALL_FACTORS:
        eval_res = evaluators[factor]()
        if eval_res is not None:
            present_factors[factor] = eval_res
        else:
            excluded_factors.append(factor)

    active_weight_sum = sum(base_weights[f] for f in present_factors)
    data_completeness = int(active_weight_sum)

    factor_breakdown: Dict[str, Any] = {}
    strengths: List[str] = []
    gaps: List[str] = []

    if active_weight_sum == 0:
        # All factors missing
        overall_score = 0
        for factor in ALL_FACTORS:
            factor_breakdown[factor] = {
                "factor": factor,
                "status": "excluded",
                "base_weight": base_weights[factor],
                "effective_weight": 0.0,
                "score": None,
                "weighted_score": 0.0,
                "details": f"Missing {factor} input data.",
            }
        gaps.append("No assessment results or profile parameters provided yet.")
        return overall_score, data_completeness, excluded_factors, factor_breakdown, strengths, gaps

    weighted_score_sum = 0.0

    for factor in ALL_FACTORS:
        base_w = base_weights[factor]
        if factor in present_factors:
            score_val, details_str = present_factors[factor]
            eff_w = base_w / active_weight_sum
            weighted_val = round(score_val * eff_w, 2)
            weighted_score_sum += score_val * eff_w

            factor_breakdown[factor] = {
                "factor": factor,
                "status": "present",
                "base_weight": base_w,
                "effective_weight": round(eff_w, 4),
                "score": score_val,
                "weighted_score": weighted_val,
                "details": details_str,
            }

            if score_val >= 75:
                strengths.append(f"Strong {factor.replace('_', ' ')}: {details_str}")
            elif score_val < 60:
                gaps.append(f"Area for growth in {factor.replace('_', ' ')}: {details_str}")
        else:
            factor_breakdown[factor] = {
                "factor": factor,
                "status": "excluded",
                "base_weight": base_w,
                "effective_weight": 0.0,
                "score": None,
                "weighted_score": 0.0,
                "details": f"No user data provided for {factor.replace('_', ' ')}.",
            }

    overall_score = int(round(weighted_score_sum))
    overall_score = max(0, min(100, overall_score))

    return overall_score, data_completeness, excluded_factors, factor_breakdown, strengths, gaps


def generate_inputs_hash(
    career_id: UUID,
    weights_version: int,
    assessment_result_id: Optional[UUID],
    profile_budget: Optional[str],
    profile_hours: Optional[int],
    profile_subjects: Optional[List[str]],
    profile_skills: Optional[List[Any]],
) -> str:
    """
    Deterministic SHA-256 hash covering assessment_result_id, profile fields, skills, and weights_version.
    """
    clean_subjects = sorted([s.strip().lower() for s in (profile_subjects or []) if s.strip()])
    clean_skills = []
    for s in (profile_skills or []):
        if isinstance(s, dict):
            s_name = str(s.get("name", "")).strip().lower()
            s_lvl = str(s.get("level", "intermediate")).strip().lower()
            clean_skills.append(f"{s_name}:{s_lvl}")
        else:
            clean_skills.append(f"{str(s).strip().lower()}:intermediate")
    clean_skills.sort()

    payload = {
        "career_id": str(career_id),
        "weights_version": weights_version,
        "assessment_result_id": str(assessment_result_id) if assessment_result_id else None,
        "budget_level": (profile_budget or "").strip().lower(),
        "hours_available_per_week": profile_hours,
        "subjects_of_interest": clean_subjects,
        "skills": clean_skills,
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_deterministic_explanation(
    overall_score: int,
    strengths: List[str],
    gaps: List[str],
    career_title: str,
) -> str:
    parts = [f"Overall compatibility with {career_title} is {overall_score}%."]
    if strengths:
        parts.append(f"Strengths: {' '.join(strengths)}")
    if gaps:
        parts.append(f"Gaps to bridge: {' '.join(gaps)}")
    return " ".join(parts)


class CompatibilityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.career_repo = CareerRepository(session)
        self.assessment_repo = AssessmentRepository(session)
        self.profile_repo = ProfileRepository(session)
        self.shortlist_repo = ShortlistRepository(session)
        self.compatibility_repo = CompatibilityRepository(session)

    async def get_compatibility(
        self,
        user: User,
        career_id: UUID,
    ) -> CompatibilitySnapshotResponse:
        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)

        career = await self.career_repo.get_by_id(career_id, allow_drafts=allow_drafts, eager_load=False)
        if not career:
            raise AppException(status_code=404, message=f"Career '{career_id}' not found or not verified.")

        latest_result = await self.assessment_repo.get_latest_result(user.id)
        profile = await self.profile_repo.get_by_user_id(user.id)

        current_hash = generate_inputs_hash(
            career_id=career.id,
            weights_version=COMPATIBILITY_WEIGHTS_V1["version"],
            assessment_result_id=latest_result.id if latest_result else None,
            profile_budget=profile.budget_level if profile else None,
            profile_hours=profile.hours_available_per_week if profile else None,
            profile_subjects=profile.subjects_of_interest if profile else None,
            profile_skills=profile.skills if profile else None,
        )

        latest_snapshot = await self.compatibility_repo.get_latest_snapshot(user.id, career.id)
        if latest_snapshot and latest_snapshot.inputs_hash == current_hash:
            # Hash matches; do not create duplicate snapshot row
            return self._build_snapshot_response(latest_snapshot, career.title)

        # Compute new score
        score, completeness, excluded, breakdown, strengths, gaps = compute_career_compatibility(
            career=career,
            assessment_result=latest_result,
            profile=profile,
            weights_config=COMPATIBILITY_WEIGHTS_V1,
        )

        template_explanation = generate_deterministic_explanation(score, strengths, gaps, career.title)

        new_snapshot = UserCareerCompatibilitySnapshot(
            user_id=user.id,
            career_id=career.id,
            overall_score=score,
            factor_breakdown=breakdown,
            strengths=strengths,
            gaps=gaps,
            weights_version=COMPATIBILITY_WEIGHTS_V1["version"],
            inputs_hash=current_hash,
            explanation_status="pending",
            ai_explanation=template_explanation,
        )
        saved = await self.compatibility_repo.save_snapshot(new_snapshot)
        return self._build_snapshot_response(saved, career.title)

    async def get_compatibility_history(
        self,
        user: User,
        career_id: UUID,
    ) -> CompatibilityHistoryResponse:
        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)

        career = await self.career_repo.get_by_id(career_id, allow_drafts=allow_drafts, eager_load=False)
        if not career:
            raise AppException(status_code=404, message=f"Career '{career_id}' not found or not verified.")

        snapshots = await self.compatibility_repo.list_history(user.id, career.id)
        items = [self._build_snapshot_response(s, career.title) for s in snapshots]
        return CompatibilityHistoryResponse(items=items, total_count=len(items))

    async def add_to_shortlist(
        self,
        user: User,
        career_id: UUID,
    ) -> ShortlistActionResponse:
        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)

        career = await self.career_repo.get_by_id(career_id, allow_drafts=allow_drafts, eager_load=False)
        if not career:
            raise AppException(status_code=404, message=f"Career '{career_id}' not found or not verified.")

        existing = await self.shortlist_repo.get_item(user.id, career.id)
        if existing:
            # Idempotent re-add
            return ShortlistActionResponse(
                status="success",
                message="Career already in shortlist.",
                career_id=career.id,
            )

        count = await self.shortlist_repo.get_count(user.id)
        if count >= 20:
            raise AppException(status_code=400, message="Shortlist limit of 20 careers reached.")

        await self.shortlist_repo.add_item(user.id, career.id)
        return ShortlistActionResponse(
            status="success",
            message="Career added to shortlist.",
            career_id=career.id,
        )

    async def remove_from_shortlist(
        self,
        user: User,
        career_id: UUID,
    ) -> ShortlistActionResponse:
        await self.shortlist_repo.remove_item(user.id, career_id)
        return ShortlistActionResponse(
            status="success",
            message="Career removed from shortlist.",
            career_id=career_id,
        )

    async def get_user_shortlist(self, user: User) -> ShortlistListResponse:
        items = await self.shortlist_repo.list_for_user(user.id)
        latest_result = await self.assessment_repo.get_latest_result(user.id)
        profile = await self.profile_repo.get_by_user_id(user.id)

        shortlist_items: List[ShortlistItemResponse] = []
        for item in items:
            c = item.career
            comp_score = None
            if c:
                latest_snap = await self.compatibility_repo.get_latest_snapshot(user.id, c.id)
                if latest_snap:
                    comp_score = latest_snap.overall_score
                else:
                    score, _, _, _, _, _ = compute_career_compatibility(
                        career=c,
                        assessment_result=latest_result,
                        profile=profile,
                    )
                    comp_score = score

                salary_schema = SalaryRangesSchema(**c.salary_ranges) if c.salary_ranges else None
                shortlist_items.append(
                    ShortlistItemResponse(
                        career_id=c.id,
                        career_title=c.title,
                        cluster=c.cluster,
                        demand=c.demand,
                        salary_ranges=salary_schema,
                        created_at=item.created_at,
                        compatibility_score=comp_score,
                    )
                )

        return ShortlistListResponse(items=shortlist_items, total_count=len(shortlist_items))

    async def compare_careers(
        self,
        user: Optional[User],
        career_ids: List[UUID],
    ) -> CompareResponse:
        # Deduplicate while preserving order
        unique_ids = list(dict.fromkeys(career_ids))
        if len(unique_ids) < 2 or len(unique_ids) > 4:
            raise AppException(
                status_code=400,
                message="Comparison requires between 2 and 4 distinct career IDs.",
            )

        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)

        careers: List[Career] = []
        for cid in unique_ids:
            career = await self.career_repo.get_by_id(cid, allow_drafts=allow_drafts, eager_load=True)
            if not career:
                raise AppException(status_code=404, message=f"Career '{cid}' not found or not verified.")
            careers.append(career)

        latest_result = None
        profile = None
        if user:
            latest_result = await self.assessment_repo.get_latest_result(user.id)
            profile = await self.profile_repo.get_by_user_id(user.id)

        items: List[CompareCareerItem] = []
        for c in careers:
            # Interest fit score
            interest_fit_score = None
            if latest_result and latest_result.dimension_scores and c.dimension_weights:
                interest_fit_score = int(round(calculate_career_similarity(latest_result.dimension_scores, c.dimension_weights) * 100.0))

            # Skills fit score
            skills_fit_score = None
            if profile and profile.skills:
                sk_eval = _evaluate_skills(c, profile)
                if sk_eval:
                    skills_fit_score = sk_eval[0]

            # Overall compatibility
            overall_score = None
            if user:
                snap = await self.compatibility_repo.get_latest_snapshot(user.id, c.id)
                if snap:
                    overall_score = snap.overall_score
                else:
                    score, _, _, _, _, _ = compute_career_compatibility(c, latest_result, profile)
                    overall_score = score

            # College fees summary
            fees_summary = None
            if c.colleges:
                fee_values = [
                    cg.fees["tuition_inr_per_year"]
                    for cg in c.colleges
                    if cg.fees and isinstance(cg.fees, dict) and "tuition_inr_per_year" in cg.fees
                ]
                if fee_values:
                    fees_summary = {
                        "min_tuition_inr_per_year": min(fee_values),
                        "max_tuition_inr_per_year": max(fee_values),
                    }

            salary_schema = SalaryRangesSchema(**c.salary_ranges) if c.salary_ranges else None

            items.append(
                CompareCareerItem(
                    career_id=c.id,
                    career_title=c.title,
                    cluster=c.cluster,
                    interest_fit_score=interest_fit_score,
                    skills_fit_score=skills_fit_score,
                    overall_compatibility_score=overall_score,
                    time_to_job_ready_months=c.time_to_job_ready_months,
                    entrance_difficulty=c.entrance_difficulty,
                    salary_ranges=salary_schema,
                    estimated_college_fees=fees_summary,
                )
            )

        ai_verdict = (
            f"Compared {len(items)} careers. Detailed qualitative AI synthesis is scheduled for Stage 2."
        )

        return CompareResponse(careers=items, ai_verdict=ai_verdict)

    def _build_snapshot_response(
        self,
        snapshot: UserCareerCompatibilitySnapshot,
        career_title: str,
    ) -> CompatibilitySnapshotResponse:
        breakdown_items: Dict[str, FactorBreakdownItem] = {}
        for factor, data in snapshot.factor_breakdown.items():
            breakdown_items[factor] = FactorBreakdownItem(
                factor=data["factor"],
                status=data["status"],
                base_weight=data["base_weight"],
                effective_weight=data["effective_weight"],
                score=data.get("score"),
                weighted_score=data["weighted_score"],
                details=data["details"],
            )

        data_completeness = sum(
            data["base_weight"]
            for data in snapshot.factor_breakdown.values()
            if data["status"] == "present"
        )
        excluded_factors = [
            f for f, data in snapshot.factor_breakdown.items()
            if data["status"] == "excluded"
        ]

        return CompatibilitySnapshotResponse(
            id=snapshot.id,
            career_id=snapshot.career_id,
            career_title=career_title,
            overall_score=snapshot.overall_score,
            data_completeness=data_completeness,
            excluded_factors=excluded_factors,
            factor_breakdown=breakdown_items,
            strengths=snapshot.strengths or [],
            gaps=snapshot.gaps or [],
            weights_version=snapshot.weights_version,
            inputs_hash=snapshot.inputs_hash,
            explanation_status=snapshot.explanation_status,
            ai_explanation=snapshot.ai_explanation,
            created_at=snapshot.created_at,
        )
