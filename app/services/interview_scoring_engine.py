import re
from typing import Any, Dict, List, Optional, Set
from app.schemas.interview import DimensionScores, ScoringResult


DEFAULT_RUBRIC_VERSION = "v1.0.0"

# Versioned rubric configuration specifying weights, caps, and heuristics
RUBRIC_CONFIGS: Dict[str, Dict[str, Any]] = {
    "v1.0.0": {
        "coverage_weight": 0.50,
        "depth_weight": 0.30,
        "structure_weight": 0.20,
        # Documented caps:
        # Fallback coverage cannot exceed 70 without AI semantic verification.
        "fallback_max_coverage_cap": 70,
        # Keyword stuffing is penalized with a strict 35 cap on coverage.
        "keyword_stuffing_coverage_cap": 35,
        "keyword_stuffing_density_threshold": 0.35,
        "min_words_for_depth": 15,
    }
}


def validate_key_points(key_points: List[Dict[str, Any]]) -> None:
    """Validates that key points are non-empty, have required fields, and weights sum to 1.0."""
    if not key_points:
        raise ValueError("key_points list must not be empty.")

    total_weight = 0.0
    seen_ids: Set[str] = set()

    for idx, kp in enumerate(key_points):
        if not isinstance(kp, dict):
            raise ValueError(f"Key point at index {idx} must be a dictionary.")

        kpid = kp.get("id")
        if not kpid or not isinstance(kpid, str) or not kpid.strip():
            raise ValueError(f"Key point at index {idx} must have a non-empty string 'id'.")
        if kpid in seen_ids:
            raise ValueError(f"Duplicate key point id '{kpid}'.")
        seen_ids.add(kpid)

        text = kp.get("text")
        if not text or not isinstance(text, str) or not text.strip():
            raise ValueError(f"Key point '{kpid}' must have a non-empty 'text' description.")

        weight = kp.get("weight")
        if weight is None or not isinstance(weight, (int, float)) or weight <= 0.0:
            raise ValueError(f"Key point '{kpid}' must have a positive numeric 'weight'.")
        total_weight += float(weight)

    if abs(total_weight - 1.0) > 0.001:
        raise ValueError(f"Key point weights must sum to 1.0 (got {total_weight:.4f}).")


def compute_scores_from_coverage(
    key_points: List[Dict[str, Any]],
    covered_points_map: Dict[str, bool],
    depth_signal: int,
    structure_signal: int,
    rubric_version: str = DEFAULT_RUBRIC_VERSION,
) -> DimensionScores:
    """Pure scoring function computing dimension scores from key-point coverage booleans,

    a depth signal, and a structure signal according to the versioned rubric config.
    Never penalises grammar, spelling, or language choice.
    """
    validate_key_points(key_points)
    config = RUBRIC_CONFIGS.get(rubric_version, RUBRIC_CONFIGS[DEFAULT_RUBRIC_VERSION])

    # 1. Coverage dimension: weighted sum of covered key points
    coverage_accum = 0.0
    covered_ids: List[str] = []

    for kp in key_points:
        kpid = kp["id"]
        if covered_points_map.get(kpid, False):
            coverage_accum += float(kp["weight"]) * 100.0
            covered_ids.append(kpid)

    coverage_score = int(round(min(100.0, max(0.0, coverage_accum))))
    clamped_depth = int(round(min(100, max(0, depth_signal))))
    clamped_structure = int(round(min(100, max(0, structure_signal))))

    # 2. Overall composite score
    cov_w = config["coverage_weight"]
    depth_w = config["depth_weight"]
    struct_w = config["structure_weight"]

    overall = int(round(
        cov_w * coverage_score + depth_w * clamped_depth + struct_w * clamped_structure
    ))
    overall = min(100, max(0, overall))

    return DimensionScores(
        coverage_score=coverage_score,
        depth_score=clamped_depth,
        structure_score=clamped_structure,
        overall_score=overall,
        covered_points=covered_ids,
        rubric_version=rubric_version,
    )


def detect_keyword_stuffing(
    tokens: List[str],
    matched_keywords: List[str],
    config: Dict[str, Any],
) -> bool:
    """Detects whether an answer is stuffing keywords without elaboration.

    Identifies comma-separated keyword dumps or repetitive term density.
    """
    if not tokens:
        return False

    total_words = len(tokens)
    if total_words < 5:
        return False

    # Count words contributed by matched keywords
    kw_words_count = 0
    for kw in matched_keywords:
        kw_tokens = re.findall(r"\b[\w'-]+\b", kw.lower())
        kw_words_count += len(kw_tokens)

    density = kw_words_count / max(1, total_words)

    # If keywords make up more than 35% of total words, or if word count is under 15 with multiple matches
    if density >= config["keyword_stuffing_density_threshold"]:
        return True
    if total_words < 15 and len(matched_keywords) >= 2:
        return True

    return False


def compute_depth_signal(answer_text: str, is_stuffed: bool = False, max_cap: Optional[int] = None) -> int:
    """Pure deterministic calculation of depth/elaboration from answer text."""
    text_lower = answer_text.lower()
    tokens = re.findall(r"\b[\w'-]+\b", text_lower)
    word_count = len(tokens)
    reasoning_terms = {
        "because", "therefore", "however", "tradeoff", "trade-off", "example",
        "complexity", "approach", "handling", "mitigate", "advantage", "disadvantage",
        "difference", "alternative", "situation", "action", "result", "impact",
    }
    has_reasoning = any(term in text_lower for term in reasoning_terms)

    if is_stuffed:
        signal = 15
    elif word_count < 20:
        signal = 25
    elif word_count < 50:
        signal = 50 + (10 if has_reasoning else 0)
    elif word_count < 120:
        signal = 65 + (15 if has_reasoning else 0)
    else:
        signal = 80 + (10 if has_reasoning else 5)

    if max_cap is not None:
        signal = min(max_cap, signal)
    return min(100, max(0, signal))


def compute_structure_signal(answer_text: str, is_stuffed: bool = False, max_cap: Optional[int] = None) -> int:
    """Pure deterministic calculation of structure/organization from answer text."""
    text_lower = answer_text.lower()
    signal = 10
    if "\n\n" in answer_text or "\n" in answer_text:
        signal += 25
    if re.search(r"(?:^|\n)\s*[-*•\d+.]\s+", answer_text):
        signal += 25
    if any(transition in text_lower for transition in ["first", "second", "third", "finally", "in summary", "to begin", "in conclusion"]):
        signal += 20
    if re.search(r"[.?!;]", answer_text):
        signal += 10

    if max_cap is not None:
        signal = min(max_cap, signal)
    return min(100, max(10, signal))


def fallback_score_answer(
    key_points: List[Dict[str, Any]],
    answer_text: str,
    rubric_version: str = DEFAULT_RUBRIC_VERSION,
) -> ScoringResult:
    """Documented keyword/phrase fallback scorer (marked fallback_scored, lower confidence,

    English-only and rough).
    Rules:
    - Never penalise grammar, spelling, or language choice.
    - Capped at fallback_max_coverage_cap (70) for normal responses.
    - Keyword stuffing is detected and capped strictly at keyword_stuffing_coverage_cap (35).
    """
    validate_key_points(key_points)
    config = RUBRIC_CONFIGS.get(rubric_version, RUBRIC_CONFIGS[DEFAULT_RUBRIC_VERSION])

    text_lower = (answer_text or "").strip().lower()
    tokens = re.findall(r"\b[\w'-]+\b", text_lower)
    word_count = len(tokens)

    if word_count == 0:
        zero_scores = DimensionScores(
            coverage_score=0,
            depth_score=0,
            structure_score=0,
            overall_score=0,
            covered_points=[],
            rubric_version=rubric_version,
        )
        return ScoringResult(
            rubric_version=rubric_version,
            scores=zero_scores,
            covered_points=[],
            scoring_method="fallback",
            confidence="low",
            details={"reason": "Empty answer"},
        )

    # 1. Match key points by keyword phrases
    covered_map: Dict[str, bool] = {}
    matched_kw_list: List[str] = []

    for kp in key_points:
        kpid = kp["id"]
        keywords = kp.get("keywords") or []
        is_matched = False

        for kw in keywords:
            kw_clean = kw.strip().lower()
            if not kw_clean:
                continue
            # Look for exact word/phrase boundary match in answer text
            pattern = r"(?<!\w)" + re.escape(kw_clean) + r"(?!\w)"
            if re.search(pattern, text_lower):
                is_matched = True
                matched_kw_list.append(kw_clean)
                break

        covered_map[kpid] = is_matched

    # 2. Check for keyword stuffing
    is_stuffed = detect_keyword_stuffing(tokens, matched_kw_list, config)

    # 3. Depth signal (evaluated purely on elaboration & reasoning, never on grammar/spelling)
    depth_signal = compute_depth_signal(answer_text, is_stuffed=is_stuffed, max_cap=85)

    # 4. Structure signal (formatting cues: paragraphs, bullet points, numbered lists, transitions)
    structure_signal = compute_structure_signal(answer_text, is_stuffed=is_stuffed, max_cap=85)

    # 5. Compute dimension scores from coverage booleans
    base_scores = compute_scores_from_coverage(
        key_points=key_points,
        covered_points_map=covered_map,
        depth_signal=depth_signal,
        structure_signal=structure_signal,
        rubric_version=rubric_version,
    )

    # 6. Apply documented caps for fallback scorer:
    # Rule A: If stuffing detected, coverage capped at 35
    # Rule B: Normal fallback coverage capped at 70 (cannot get 100 via heuristic alone)
    coverage = base_scores.coverage_score
    if is_stuffed:
        coverage = min(coverage, config["keyword_stuffing_coverage_cap"])
    else:
        coverage = min(coverage, config["fallback_max_coverage_cap"])

    cov_w = config["coverage_weight"]
    depth_w = config["depth_weight"]
    struct_w = config["structure_weight"]
    overall = int(round(cov_w * coverage + depth_w * depth_signal + struct_w * structure_signal))
    overall = min(100, max(0, overall))

    final_scores = DimensionScores(
        coverage_score=coverage,
        depth_score=depth_signal,
        structure_score=structure_signal,
        overall_score=overall,
        covered_points=base_scores.covered_points,
        rubric_version=rubric_version,
    )

    return ScoringResult(
        rubric_version=rubric_version,
        scores=final_scores,
        covered_points=base_scores.covered_points,
        scoring_method="fallback",
        confidence="low",
        details={
            "is_stuffed": is_stuffed,
            "word_count": word_count,
            "matched_keywords_count": len(matched_kw_list),
            "max_coverage_cap_applied": not is_stuffed and base_scores.coverage_score > config["fallback_max_coverage_cap"],
        },
    )
