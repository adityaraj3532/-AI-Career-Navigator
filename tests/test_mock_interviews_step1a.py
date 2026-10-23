import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.interview_repository import (
    ActiveSessionExistsError,
    InsufficientQuestionsError,
)
from app.schemas.interview import InterviewQuestionCreate, KeyPointItem
from app.services.interview_scoring_engine import (
    DEFAULT_RUBRIC_VERSION,
    RUBRIC_CONFIGS,
    compute_scores_from_coverage,
    fallback_score_answer,
    validate_key_points,
)


@pytest.fixture
def sample_key_points():
    return [
        {
            "id": "kp_1",
            "text": "Mentions time complexity O(N log N)",
            "weight": 0.40,
            "keywords": ["o(n log n)", "nlogn", "time complexity", "quicksort"],
        },
        {
            "id": "kp_2",
            "text": "Explains space complexity and in-place sorting trade-off",
            "weight": 0.30,
            "keywords": ["space complexity", "in-place", "auxiliary space", "o(1)"],
        },
        {
            "id": "kp_3",
            "text": "Considers worst-case inputs and stability",
            "weight": 0.30,
            "keywords": ["worst case", "stability", "stable", "pivot"],
        },
    ]


def test_validate_key_points_weights_sum_to_one(sample_key_points):
    # Valid: weights sum to 1.0 (0.4 + 0.3 + 0.3)
    validate_key_points(sample_key_points)

    # Invalid: weights sum to 0.8
    bad_points = [
        {"id": "kp_1", "text": "Point 1", "weight": 0.5},
        {"id": "kp_2", "text": "Point 2", "weight": 0.3},
    ]
    with pytest.raises(ValueError, match="Key point weights must sum to 1.0"):
        validate_key_points(bad_points)

    # Invalid: empty list
    with pytest.raises(ValueError, match="must not be empty"):
        validate_key_points([])


def test_schema_validates_key_point_weights():
    # Pydantic schema validation
    valid_create = InterviewQuestionCreate(
        type="technical",
        level="intermediate",
        text="Explain binary search complexity and edge cases.",
        key_points=[
            KeyPointItem(id="kp_1", text="O(log N) time", weight=0.6, keywords=["o(log n)"]),
            KeyPointItem(id="kp_2", text="Sorted input required", weight=0.4, keywords=["sorted"]),
        ],
    )
    assert len(valid_create.key_points) == 2

    with pytest.raises(ValueError, match="Key point weights must sum to 1.0"):
        InterviewQuestionCreate(
            type="technical",
            level="intermediate",
            text="Explain binary search complexity and edge cases.",
            key_points=[
                KeyPointItem(id="kp_1", text="O(log N) time", weight=0.4, keywords=["o(log n)"]),
                KeyPointItem(id="kp_2", text="Sorted input required", weight=0.4, keywords=["sorted"]),
            ],
        )


def test_scoring_no_points_covered(sample_key_points):
    coverage_map = {"kp_1": False, "kp_2": False, "kp_3": False}
    scores = compute_scores_from_coverage(
        key_points=sample_key_points,
        covered_points_map=coverage_map,
        depth_signal=0,
        structure_signal=0,
    )
    assert scores.coverage_score == 0
    assert scores.depth_score == 0
    assert scores.structure_score == 0
    assert scores.overall_score == 0
    assert scores.covered_points == []
    assert scores.rubric_version == DEFAULT_RUBRIC_VERSION


def test_scoring_all_points_covered(sample_key_points):
    coverage_map = {"kp_1": True, "kp_2": True, "kp_3": True}
    scores = compute_scores_from_coverage(
        key_points=sample_key_points,
        covered_points_map=coverage_map,
        depth_signal=100,
        structure_signal=100,
    )
    assert scores.coverage_score == 100
    assert scores.depth_score == 100
    assert scores.structure_score == 100
    assert scores.overall_score == 100
    assert set(scores.covered_points) == {"kp_1", "kp_2", "kp_3"}


def test_scoring_partial_coverage(sample_key_points):
    # Only kp_1 (weight 0.40) and kp_3 (weight 0.30) covered -> coverage = 70
    coverage_map = {"kp_1": True, "kp_2": False, "kp_3": True}
    scores = compute_scores_from_coverage(
        key_points=sample_key_points,
        covered_points_map=coverage_map,
        depth_signal=60,
        structure_signal=80,
    )
    assert scores.coverage_score == 70
    assert scores.depth_score == 60
    assert scores.structure_score == 80
    # Expected overall = 0.50 * 70 + 0.30 * 60 + 0.20 * 80 = 35 + 18 + 16 = 69
    assert scores.overall_score == 69
    assert scores.covered_points == ["kp_1", "kp_3"]


def test_fallback_scorer_normal_elaborated_answer(sample_key_points):
    answer = (
        "Quicksort achieves an average time complexity of O(N log N) by picking a pivot element.\n\n"
        "Regarding memory, it operates in-place with O(1) auxiliary space beyond the recursion stack.\n\n"
        "However, in the worst case when the pivot is poorly chosen, it degrades to O(N^2), "
        "and standard implementations lack stability because equal elements can be swapped."
    )
    result = fallback_score_answer(sample_key_points, answer)
    assert result.scoring_method == "fallback"
    assert result.confidence == "low"
    assert result.rubric_version == DEFAULT_RUBRIC_VERSION
    assert "kp_1" in result.covered_points
    assert "kp_2" in result.covered_points
    assert "kp_3" in result.covered_points
    # Documented cap: normal fallback coverage is capped at 70 (cannot reach 100 via heuristic alone)
    assert result.scores.coverage_score == 70
    assert result.scores.depth_score > 50
    assert result.scores.structure_score >= 40
    assert result.scores.overall_score > 50


def test_fallback_scorer_keyword_stuffing_strictly_capped(sample_key_points):
    # Pure keyword stuffing dump with zero elaboration
    stuffed_answer = "O(N log N) Quicksort in-place worst case stability time complexity space complexity"
    result = fallback_score_answer(sample_key_points, stuffed_answer)

    assert result.details["is_stuffed"] is True
    # Documented cap: keyword stuffing coverage is strictly capped at 35
    assert result.scores.coverage_score <= RUBRIC_CONFIGS["v1.0.0"]["keyword_stuffing_coverage_cap"]
    assert result.scores.depth_score <= 20
    assert result.confidence == "low"


def test_fallback_scorer_maximum_cap_documentation(sample_key_points):
    # Even a comprehensive answer matched across all points is capped at 70 in fallback
    rich_answer = (
        "First, the time complexity of quicksort is O(N log N) on average due to divide and conquer.\n"
        "Second, space complexity is in-place requiring minimal auxiliary space.\n"
        "Third, worst case occurs on sorted arrays without random pivot, and stability is not guaranteed.\n"
        "In summary, we tradeoff stability for high CPU cache performance."
    )
    result = fallback_score_answer(sample_key_points, rich_answer)
    assert result.scores.coverage_score == RUBRIC_CONFIGS["v1.0.0"]["fallback_max_coverage_cap"]
    assert result.scores.coverage_score == 70


def test_no_grammar_spelling_penalty(sample_key_points):
    # Answer with grammatical quirks, misspellings and informal English
    informal_answer = (
        "sir time complexity is o(n log n) average coz of pivot.\n\n"
        "also its totally in-place so space complexity is very very less.\n\n"
        "but worst case can happen if bad pivot and stability is not there."
    )
    result = fallback_score_answer(sample_key_points, informal_answer)
    # Coverage must NOT be penalized for grammar, spelling, or dialect
    assert result.scores.coverage_score == 70
    assert set(result.covered_points) == {"kp_1", "kp_2", "kp_3"}


def test_rubric_version_stored_on_result(sample_key_points):
    result = fallback_score_answer(sample_key_points, "Time complexity is O(N log N)", rubric_version="v1.0.0")
    assert result.rubric_version == "v1.0.0"
    assert result.scores.rubric_version == "v1.0.0"


@pytest.mark.asyncio
async def test_draft_questions_hidden_by_default(test_storage):
    from tests.conftest import InMemoryInterviewRepo
    repo = InMemoryInterviewRepo(test_storage)

    sde = next((c for c in test_storage["careers"].values() if c.code == "SOFTWARE_DEVELOPER"), None)
    assert sde is not None

    # By default, questions are seeded as 'draft'.
    # get_questions_for_interview with allow_drafts=False must raise InsufficientQuestionsError
    with pytest.raises(InsufficientQuestionsError, match="verified in bank"):
        await repo.get_questions_for_interview(
            career_id=sde.id,
            type="technical",
            level="beginner",
            limit=1,
            allow_drafts=False,
        )

    # When allow_drafts=True (development mode), draft questions are accessible
    draft_qs = await repo.get_questions_for_interview(
        career_id=sde.id,
        type="technical",
        level="beginner",
        limit=1,
        allow_drafts=True,
    )
    assert len(draft_qs) == 1
    assert draft_qs[0].status == "draft"


@pytest.mark.asyncio
async def test_session_snapshot_unaffected_by_question_edits(test_storage):
    from tests.conftest import InMemoryInterviewRepo
    repo = InMemoryInterviewRepo(test_storage)

    sde = next((c for c in test_storage["careers"].values() if c.code == "SOFTWARE_DEVELOPER"), None)
    user_id = uuid4()

    # Get a draft question to start session
    qs = await repo.get_questions_for_interview(
        career_id=sde.id,
        type="technical",
        level="beginner",
        limit=1,
        allow_drafts=True,
    )
    original_q = qs[0]
    orig_text = original_q.text
    orig_key_points = list(original_q.key_points)

    # Create session with snapshot
    session = await repo.create_session(
        user_id=user_id,
        career_id=sde.id,
        type="technical",
        level="beginner",
        questions=[original_q],
    )
    sq = session.session_questions[0]
    assert sq.question_text == orig_text
    assert sq.key_points == orig_key_points

    # Mutate the original InterviewQuestion template
    original_q.text = "MUTATED QUESTION TEXT AFTER CREATION"
    original_q.key_points = [{"id": "kp_mutated", "text": "Mutated", "weight": 1.0}]

    # Invariant: session_question snapshot remains unchanged!
    assert sq.question_text == orig_text
    assert sq.key_points == orig_key_points
    assert sq.question_text != original_q.text


@pytest.mark.asyncio
async def test_one_active_session_per_user(test_storage):
    from tests.conftest import InMemoryInterviewRepo
    repo = InMemoryInterviewRepo(test_storage)

    sde = next((c for c in test_storage["careers"].values() if c.code == "SOFTWARE_DEVELOPER"), None)
    user_id = uuid4()

    qs = await repo.get_questions_for_interview(
        career_id=sde.id,
        type="technical",
        level="beginner",
        limit=1,
        allow_drafts=True,
    )

    # First session creation succeeds
    session_1 = await repo.create_session(
        user_id=user_id,
        career_id=sde.id,
        type="technical",
        level="beginner",
        questions=qs,
    )
    assert session_1.status == "in_progress"

    # Second concurrent session creation fails with ActiveSessionExistsError
    with pytest.raises(ActiveSessionExistsError, match="already has an active interview session"):
        await repo.create_session(
            user_id=user_id,
            career_id=sde.id,
            type="technical",
            level="beginner",
            questions=qs,
        )


@pytest.mark.asyncio
async def test_verify_cli_marks_questions_verified(test_storage):
    from tests.conftest import InMemoryInterviewRepo
    repo = InMemoryInterviewRepo(test_storage)

    sde = next((c for c in test_storage["careers"].values() if c.code == "SOFTWARE_DEVELOPER"), None)
    qs = await repo.get_questions_for_interview(
        career_id=sde.id,
        type="technical",
        level="beginner",
        limit=1,
        allow_drafts=True,
    )
    q = qs[0]
    assert q.status == "draft"

    # Simulate CLI verification
    q.status = "verified"
    q.last_verified_by = "lead_tech_reviewer@example.com"
    q.last_verified_at = datetime.now(timezone.utc)

    # Now verified question query succeeds with allow_drafts=False
    verified_qs = await repo.get_questions_for_interview(
        career_id=sde.id,
        type="technical",
        level="beginner",
        limit=1,
        allow_drafts=False,
    )
    assert len(verified_qs) == 1
    assert verified_qs[0].id == q.id
    assert verified_qs[0].status == "verified"
    assert verified_qs[0].last_verified_by == "lead_tech_reviewer@example.com"
