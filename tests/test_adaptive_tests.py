from datetime import datetime, timedelta, timezone
from uuid import UUID
import pytest
from httpx import AsyncClient

from app.services.adaptive_test_engine import (
    calculate_next_difficulty,
    evaluate_final_level,
)


# ---------------------------------------------------------------------------
# Unit Tests: Pure Engine Functions
# ---------------------------------------------------------------------------

def test_progression_rule_cases():
    """Verify 3-step ladder progression transitions and boundaries."""
    # From level 2:
    assert calculate_next_difficulty(2, is_correct=True) == 3
    assert calculate_next_difficulty(2, is_correct=False) == 1

    # From level 3 (ceiling):
    assert calculate_next_difficulty(3, is_correct=True) == 3
    assert calculate_next_difficulty(3, is_correct=False) == 2

    # From level 1 (floor):
    assert calculate_next_difficulty(1, is_correct=False) == 1
    assert calculate_next_difficulty(1, is_correct=True) == 2


def test_final_level_all_correct_reaches_advanced():
    """All correct answers with at least 2 at difficulty 3 reaches advanced."""
    answers = [
        {"difficulty": 2, "is_correct": True},
        {"difficulty": 3, "is_correct": True},
        {"difficulty": 3, "is_correct": True},
        {"difficulty": 3, "is_correct": True},
        {"difficulty": 3, "is_correct": True},
        {"difficulty": 3, "is_correct": True},
    ]
    level, conf, score_pct, total_corr, recs, disclaimer = evaluate_final_level(answers)
    assert level == "advanced"
    assert conf == "high"
    assert score_pct == 100
    assert total_corr == 6
    assert len(recs) > 0
    assert "preliminary estimate" in disclaimer.lower()


def test_final_level_all_wrong_reaches_beginner():
    """All wrong answers stepladders to difficulty 1 and reaches beginner."""
    answers = [
        {"difficulty": 2, "is_correct": False},
        {"difficulty": 1, "is_correct": False},
        {"difficulty": 1, "is_correct": False},
        {"difficulty": 1, "is_correct": False},
        {"difficulty": 1, "is_correct": False},
        {"difficulty": 1, "is_correct": False},
    ]
    level, conf, score_pct, total_corr, _, _ = evaluate_final_level(answers)
    assert level == "beginner"
    assert score_pct == 0
    assert total_corr == 0


def test_final_level_alternating_reaches_intermediate():
    """Alternating between 2 and 3 converges to intermediate."""
    answers = [
        {"difficulty": 2, "is_correct": True},
        {"difficulty": 3, "is_correct": False},
        {"difficulty": 2, "is_correct": True},
        {"difficulty": 3, "is_correct": False},
        {"difficulty": 2, "is_correct": True},
        {"difficulty": 3, "is_correct": False},
    ]
    level, conf, score_pct, total_corr, _, _ = evaluate_final_level(answers)
    assert level == "intermediate"
    assert score_pct == 50
    assert total_corr == 3


def test_final_level_minimum_answers_boundary():
    """Even with 100% accuracy on difficulty 3, having < 2 answers at diff 3 prevents reaching advanced."""
    answers = [
        {"difficulty": 2, "is_correct": True},
        {"difficulty": 3, "is_correct": True},
        {"difficulty": 2, "is_correct": False},
    ]
    # d3 count is only 1 (< 2 required)
    level, conf, score_pct, _, _, _ = evaluate_final_level(answers)
    assert level != "advanced"
    assert level == "intermediate"
    assert conf == "medium"


def test_final_level_early_finish_low_sample():
    """Low answer count (< 3 answers) returns low confidence."""
    answers = [
        {"difficulty": 2, "is_correct": True},
    ]
    level, conf, score_pct, total_corr, _, _ = evaluate_final_level(answers)
    assert conf == "low"


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------

async def _signup_and_login(client: AsyncClient, email: str) -> str:
    signup_res = await client.post(
        "/v1/auth/signup",
        json={"email": email, "password": "Password123!", "education_level": "college"},
    )
    assert signup_res.status_code == 201

    login_res = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_res.status_code == 200
    return login_res.json()["access_token"]


@pytest.fixture(autouse=True)
def setup_test_catalog_and_questions(test_storage):
    """Ensure test careers and test questions are verified for API integration."""
    for c in test_storage["careers"].values():
        c.status = "verified"
    for q in test_storage["test_question_banks"].values():
        q.status = "verified"


@pytest.mark.asyncio
async def test_no_answer_leakage_in_start_and_next_question(async_client: AsyncClient, test_storage):
    """Test that correct_option_id and explanation are NEVER present in public question payloads."""
    token = await _signup_and_login(async_client, "leak_check@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    career_id = list(test_storage["careers"].keys())[0]

    # 1. Start test
    start_res = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python", "language": "python"},
        headers=headers,
    )
    assert start_res.status_code == 201
    start_data = start_res.json()
    first_q = start_data["current_question"]

    # Verify no correct answer or explanation in start payload
    assert "correct_option_id" not in first_q
    assert "explanation" not in first_q
    assert "correct_answer" not in first_q
    for opt in first_q["options"]:
        assert "is_correct" not in opt

    # 2. Answer question
    test_id = start_data["test_id"]
    ans_res = await async_client.post(
        f"/v1/tests/{test_id}/answer",
        json={"question_id": first_q["id"], "selected_option_id": "opt_a", "time_taken_seconds": 15},
        headers=headers,
    )
    assert ans_res.status_code == 200
    ans_data = ans_res.json()

    # The answered question's explanation and correctness ARE returned
    assert "is_correct" in ans_data
    assert "explanation" in ans_data
    assert len(ans_data["explanation"]) > 0

    # But the NEXT question still has NO answer leakage
    next_q = ans_data["next_question"]
    assert next_q is not None
    assert "correct_option_id" not in next_q
    assert "explanation" not in next_q
    assert "correct_answer" not in next_q


@pytest.mark.asyncio
async def test_full_test_lifecycle_and_adaptive_progression(async_client: AsyncClient, test_storage):
    """Walkthrough of complete adaptive test: start -> answer all 6 questions -> finish."""
    token = await _signup_and_login(async_client, "lifecycle@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    career_id = list(test_storage["careers"].keys())[0]

    start_res = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "dsa"},
        headers=headers,
    )
    assert start_res.status_code == 201
    start_data = start_res.json()
    test_id = start_data["test_id"]

    current_q = start_data["current_question"]
    assert current_q["difficulty"] == 2  # Always starts at difficulty 2

    # Answer all 6 questions
    for i in range(1, 7):
        ans_res = await async_client.post(
            f"/v1/tests/{test_id}/answer",
            json={"question_id": current_q["id"], "selected_option_id": "opt_a"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        ans_data = ans_res.json()
        assert ans_data["current_question_index"] == i

        if i < 6:
            assert ans_data["can_finish"] is False
            assert ans_data["next_question"] is not None
            current_q = ans_data["next_question"]
        else:
            assert ans_data["can_finish"] is True
            assert ans_data["next_question"] is None

    # Finish test
    fin_res = await async_client.post(f"/v1/tests/{test_id}/finish", json={}, headers=headers)
    assert fin_res.status_code == 200
    fin_data = fin_res.json()
    assert fin_data["status"] == "finished"
    assert fin_data["total_questions"] == 6
    assert fin_data["demonstrated_level"] in ("beginner", "intermediate", "advanced")
    assert fin_data["confidence"] in ("low", "medium", "high")
    assert len(fin_data["recommendations"]) > 0

    # Idempotent re-finish returns same results
    fin_res2 = await async_client.post(f"/v1/tests/{test_id}/finish", json={}, headers=headers)
    assert fin_res2.status_code == 200
    assert fin_res2.json()["test_id"] == fin_data["test_id"]


@pytest.mark.asyncio
async def test_double_answer_idempotency(async_client: AsyncClient, test_storage):
    """Submitting the same answer is idempotent; submitting a different answer is rejected."""
    token = await _signup_and_login(async_client, "double_ans@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career_id = list(test_storage["careers"].keys())[0]

    start_res = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python"},
        headers=headers,
    )
    test_id = start_res.json()["test_id"]
    qid = start_res.json()["current_question"]["id"]

    # First answer submission
    r1 = await async_client.post(
        f"/v1/tests/{test_id}/answer",
        json={"question_id": qid, "selected_option_id": "opt_a"},
        headers=headers,
    )
    assert r1.status_code == 200

    # Idempotent re-submission of exact same answer succeeds
    r2 = await async_client.post(
        f"/v1/tests/{test_id}/answer",
        json={"question_id": qid, "selected_option_id": "opt_a"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["is_correct"] == r1.json()["is_correct"]

    # Modifying the answer to an already answered question returns 400
    r3 = await async_client.post(
        f"/v1/tests/{test_id}/answer",
        json={"question_id": qid, "selected_option_id": "opt_b"},
        headers=headers,
    )
    assert r3.status_code == 400
    assert "already been answered" in r3.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_answering_after_expiry(async_client: AsyncClient, test_storage):
    """Answering an expired test attempt is rejected with 400."""
    token = await _signup_and_login(async_client, "expiry_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career_id = list(test_storage["careers"].keys())[0]

    start_res = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python"},
        headers=headers,
    )
    test_id = UUID(start_res.json()["test_id"])
    qid = start_res.json()["current_question"]["id"]

    # Manually expire the attempt in test_storage
    test_storage["test_attempts"][test_id].expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    ans_res = await async_client.post(
        f"/v1/tests/{test_id}/answer",
        json={"question_id": qid, "selected_option_id": "opt_a"},
        headers=headers,
    )
    assert ans_res.status_code == 400
    assert "expired" in ans_res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_one_active_attempt_enforced(async_client: AsyncClient, test_storage):
    """Starting a second attempt on the same topic while one is active returns 400."""
    token = await _signup_and_login(async_client, "active_attempt@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career_id = list(test_storage["careers"].keys())[0]

    r1 = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python"},
        headers=headers,
    )
    assert r1.status_code == 201

    # Second start on same topic
    r2 = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python"},
        headers=headers,
    )
    assert r2.status_code == 400
    assert "active test attempt already exists" in r2.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_retake_cooldown_enforced(async_client: AsyncClient, test_storage):
    """Attempting to retake a topic within cooldown period returns 400."""
    token = await _signup_and_login(async_client, "cooldown_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career_id = list(test_storage["careers"].keys())[0]

    r1 = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "aptitude", "topic": "quantitative_aptitude"},
        headers=headers,
    )
    test_id = r1.json()["test_id"]

    # Finish attempt
    fin = await async_client.post(f"/v1/tests/{test_id}/finish", json={}, headers=headers)
    assert fin.status_code == 200

    # Immediate retake should be blocked by cooldown
    r2 = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "aptitude", "topic": "quantitative_aptitude"},
        headers=headers,
    )
    assert r2.status_code == 400
    assert "cooldown active" in r2.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_ownership_isolation(async_client: AsyncClient, test_storage):
    """Accessing another user's test attempt returns 404."""
    u1_token = await _signup_and_login(async_client, "owner_u1@example.com")
    u2_token = await _signup_and_login(async_client, "intruder_u2@example.com")
    career_id = list(test_storage["careers"].keys())[0]

    # User 1 starts test
    r1 = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python"},
        headers={"Authorization": f"Bearer {u1_token}"},
    )
    test_id = r1.json()["test_id"]
    qid = r1.json()["current_question"]["id"]

    # User 2 attempts to answer User 1's test -> 404
    ans_u2 = await async_client.post(
        f"/v1/tests/{test_id}/answer",
        json={"question_id": qid, "selected_option_id": "opt_a"},
        headers={"Authorization": f"Bearer {u2_token}"},
    )
    assert ans_u2.status_code == 404

    # User 2 attempts to finish User 1's test -> 404
    fin_u2 = await async_client.post(
        f"/v1/tests/{test_id}/finish",
        json={},
        headers={"Authorization": f"Bearer {u2_token}"},
    )
    assert fin_u2.status_code == 404


@pytest.mark.asyncio
async def test_draft_questions_hidden_by_default(async_client: AsyncClient, test_storage):
    """When questions are in draft status, starting test returns insufficient verified questions error."""
    # Set all questions to draft
    for q in test_storage["test_question_banks"].values():
        q.status = "draft"

    token = await _signup_and_login(async_client, "draft_q_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career_id = list(test_storage["careers"].keys())[0]

    res = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "not enough verified questions" in res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_extra_fields_forbidden(async_client: AsyncClient, test_storage):
    """Verify extra='forbid' on request bodies."""
    token = await _signup_and_login(async_client, "extra_fields@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career_id = list(test_storage["careers"].keys())[0]

    # Extra field on start
    r1 = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python", "hacked_field": True},
        headers=headers,
    )
    assert r1.status_code == 422


@pytest.mark.asyncio
async def test_get_test_history(async_client: AsyncClient, test_storage):
    """Verify paginated test history returns only current user's attempts."""
    token = await _signup_and_login(async_client, "history_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career_id = list(test_storage["careers"].keys())[0]

    # Start and finish an attempt
    start_res = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(career_id), "type": "skill", "topic": "python"},
        headers=headers,
    )
    assert start_res.status_code == 201
    test_id = start_res.json()["test_id"]

    await async_client.post(
        f"/v1/tests/{test_id}/finish",
        json={},
        headers=headers,
    )

    # Fetch history
    res = await async_client.get("/v1/tests/history?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == test_id
    assert data["items"][0]["topic"] == "python"
    assert data["items"][0]["status"] == "finished"


@pytest.mark.asyncio
async def test_language_advisor(async_client: AsyncClient, test_storage):
    """Verify deterministic language advisor questionnaire response."""
    token = await _signup_and_login(async_client, "advisor_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Test ML goal -> Python
    res_ml = await async_client.post(
        "/v1/tests/language-advisor",
        json={"primary_goal": "machine_learning", "prior_experience": "beginner"},
        headers=headers,
    )
    assert res_ml.status_code == 200
    d_ml = res_ml.json()
    assert d_ml["recommended_language"] == "python"
    assert "why_it_fits" in d_ml
    assert len(d_ml["next_steps"]) > 0

    # Test systems goal with intermediate experience -> Rust
    res_sys = await async_client.post(
        "/v1/tests/language-advisor",
        json={"primary_goal": "embedded_systems", "prior_experience": "intermediate"},
        headers=headers,
    )
    assert res_sys.status_code == 200
    d_sys = res_sys.json()
    assert d_sys["recommended_language"] == "rust"

