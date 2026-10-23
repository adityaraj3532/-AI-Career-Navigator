from datetime import datetime, timedelta, timezone
from typing import Tuple
from uuid import uuid4
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.adaptive_test import (
    TestQuestionBank as ModelTestQuestionBank,
)
from app.models.career import Career
from app.models.user import User
from app.services.skill_tracker_engine import (
    analyze_subtopics,
    compute_evidence_weight,
    compute_skill_level_and_confidence,
    compute_trend_over_time,
    generate_fallback_report_text,
    level_to_value,
    score_to_level_value,
    value_to_level,
)


# ==============================================================================
# PURE ENGINE UNIT TESTS
# ==============================================================================

def test_engine_level_and_score_conversions():
    assert level_to_value("beginner") == 1.0
    assert level_to_value("intermediate") == 2.0
    assert level_to_value("advanced") == 3.0
    assert level_to_value("unknown") == 1.0

    assert value_to_level(3.0) == "advanced"
    assert value_to_level(2.5) == "advanced"
    assert value_to_level(2.4) == "intermediate"
    assert value_to_level(1.6) == "intermediate"
    assert value_to_level(1.5) == "beginner"

    assert score_to_level_value(90) == 3.0
    assert score_to_level_value(80) == 3.0
    assert score_to_level_value(65) == 2.0
    assert score_to_level_value(50) == 2.0
    assert score_to_level_value(30) == 1.0


def test_engine_declared_skill_cap_at_beginner():
    # User declares "advanced", but declared evidence is capped at beginner (1.0)
    now = datetime.now(timezone.utc)
    evidence = [
        {"source_type": "declared", "level_signal": "advanced", "created_at": now}
    ]
    level, conf, num_val = compute_skill_level_and_confidence(evidence, now=now)
    assert level == "beginner"
    assert conf == "low"  # weight 0.15 < 0.8
    assert num_val == 1.0


def test_engine_roadmap_evidence_cap_at_intermediate():
    # User completes a roadmap step with high score; roadmap cap is 2.0 ("intermediate")
    now = datetime.now(timezone.utc)
    evidence = [
        {"source_type": "roadmap", "score": 95, "created_at": now}
    ]
    level, conf, num_val = compute_skill_level_and_confidence(evidence, now=now)
    assert level == "intermediate"
    assert num_val == 2.0


def test_engine_non_test_overall_cap():
    # Even with declared + roadmap + project without test, non-test caps apply
    now = datetime.now(timezone.utc)
    evidence = [
        {"source_type": "declared", "level_signal": "advanced", "created_at": now},
        {"source_type": "roadmap", "score": 90, "created_at": now},
    ]
    # No test, max allowed cap is roadmap (2.0)
    level, conf, num_val = compute_skill_level_and_confidence(evidence, now=now)
    assert level == "intermediate"
    assert num_val <= 2.0


def test_engine_test_evidence_reaches_advanced():
    now = datetime.now(timezone.utc)
    evidence = [
        {"source_type": "test", "level_signal": "advanced", "score": 90, "created_at": now},
        {"source_type": "test", "level_signal": "advanced", "score": 85, "created_at": now},
    ]
    level, conf, num_val = compute_skill_level_and_confidence(evidence, now=now)
    assert level == "advanced"
    assert conf == "high"  # total weight 2.0 >= 1.8 and has_test is True
    assert num_val >= 2.5


def test_engine_recency_decay():
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=60)  # 2 half-lives (30 days each) -> weight * 0.25
    weight_now = compute_evidence_weight("test", now, now=now)
    weight_old = compute_evidence_weight("test", old_date, now=now)

    assert abs(weight_now - 1.0) < 1e-4
    assert abs(weight_old - 0.25) < 1e-4

    # Combined: old advanced test + recent beginner test -> recent beginner test has higher weight
    evidence = [
        {"source_type": "test", "level_signal": "advanced", "created_at": old_date},
        {"source_type": "test", "level_signal": "beginner", "created_at": now},
    ]
    level, _, num_val = compute_skill_level_and_confidence(evidence, now=now)
    # 0.25 * 3.0 + 1.0 * 1.0 = 1.75 / 1.25 = 1.4 -> "beginner"
    assert level == "beginner"
    assert num_val < 1.6


def test_engine_subtopic_analysis():
    evidence = [
        {"subtopic_scores": {"Arrays": 80, "Trees": 40, "Dynamic Programming": 50}},
        {"subtopic_scores": {"Arrays": 90, "Trees": 55, "Dynamic Programming": 65}},
    ]
    strengths, weaknesses = analyze_subtopics(evidence)
    assert "Arrays" in strengths  # avg 85% >= 70%
    assert "Trees" in weaknesses  # avg 47.5% < 60%
    assert "Dynamic Programming" not in strengths
    assert "Dynamic Programming" in weaknesses  # avg 57.5% <= 59% -> weakness


def test_engine_trend_null_when_less_than_two_items():
    assert compute_trend_over_time([]) is None
    assert compute_trend_over_time([{"source_type": "declared", "created_at": datetime.now(timezone.utc)}]) is None


def test_engine_trend_calculated_when_two_or_more_items():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 15, tzinfo=timezone.utc)
    evidence = [
        {"source_type": "test", "level_signal": "beginner", "score": 30, "created_at": t0},
        {"source_type": "test", "level_signal": "advanced", "score": 90, "created_at": t1},
    ]
    trend = compute_trend_over_time(evidence)
    assert trend is not None
    assert trend["direction"] == "improving"
    assert trend["start_level"] == "beginner"
    assert trend["current_level"] == "intermediate"
    assert len(trend["history"]) == 2


def test_engine_fallback_report_text():
    text = generate_fallback_report_text(
        skill_name="Python",
        level="intermediate",
        confidence="medium",
        strengths=["FastAPI", "OOP"],
        weaknesses=["Metaclasses"],
        evidence_count=3,
    )
    assert "Skill Report for Python" in text
    assert "Intermediate" in text
    assert "FastAPI, OOP" in text
    assert "Metaclasses" in text


# ==============================================================================
# API INTEGRATION TESTS
# ==============================================================================

async def _create_test_user(test_storage, email="student_skill@example.com") -> Tuple[User, str]:
    uid = uuid4()
    user = User(
        id=uid,
        email=email,
        hashed_password="hash",
        role="student",
        education_level="college_technical",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_storage["users"][uid] = user
    token = create_access_token(uid, user.email, user.role)
    return user, token


@pytest.mark.asyncio
async def test_declare_skill_success(async_client: AsyncClient, test_storage):
    user, token = await _create_test_user(test_storage, "declare_ok@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Declare by slug
    resp = await async_client.post(
        "/v1/skills/declare",
        json={"skill_slug": "python", "level": "intermediate"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["skill_slug"] == "python"
    assert data["skill_name"] == "Python"
    # Even though user said intermediate, declared skills alone are capped at beginner!
    assert data["current_level"] == "beginner"
    assert data["confidence"] == "low"


@pytest.mark.asyncio
async def test_declare_skill_extra_forbidden(async_client: AsyncClient, test_storage):
    _, token = await _create_test_user(test_storage, "extra_forbid@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        "/v1/skills/declare",
        json={"skill_slug": "python", "level": "beginner", "extra_param": "not_allowed"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_declare_skill_not_found(async_client: AsyncClient, test_storage):
    _, token = await _create_test_user(test_storage, "notfound_skill@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        "/v1/skills/declare",
        json={"skill_slug": "non_existent_skill_xyz", "level": "beginner"},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_user_skills(async_client: AsyncClient, test_storage):
    user, token = await _create_test_user(test_storage, "list_skills@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Initially empty
    resp = await async_client.get("/v1/skills", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["skills"] == []
    assert resp.json()["total_count"] == 0

    # Declare one skill
    await async_client.post(
        "/v1/skills/declare",
        json={"skill_slug": "dsa", "level": "beginner"},
        headers=headers,
    )

    resp2 = await async_client.get("/v1/skills", headers=headers)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["total_count"] == 1
    assert data["skills"][0]["skill_slug"] == "dsa"


@pytest.mark.asyncio
async def test_get_skill_report_ownership_and_data(async_client: AsyncClient, test_storage):
    user1, token1 = await _create_test_user(test_storage, "user1_report@example.com")
    user2, token2 = await _create_test_user(test_storage, "user2_report@example.com")

    h1 = {"Authorization": f"Bearer {token1}"}
    h2 = {"Authorization": f"Bearer {token2}"}

    # User 1 declares dsa
    decl_resp = await async_client.post(
        "/v1/skills/declare",
        json={"skill_slug": "dsa", "level": "intermediate"},
        headers=h1,
    )
    skill_id = decl_resp.json()["skill_id"]

    # User 2 attempts to view User 1's skill report -> returns 404 (Ownership invariant)
    resp_unowned = await async_client.get(f"/v1/skills/{skill_id}/report", headers=h2)
    assert resp_unowned.status_code == 404

    # User 1 views their own report -> 200 OK
    resp_owned = await async_client.get(f"/v1/skills/{skill_id}/report", headers=h1)
    assert resp_owned.status_code == 200
    rep = resp_owned.json()
    assert rep["skill_slug"] == "dsa"
    assert rep["report_status"] == "fallback"
    assert "Skill Report for Data Structures & Algorithms" in rep["report_text"]
    assert rep["evidence_count"] == 1
    # Only 1 evidence point -> trend MUST strictly be None
    assert rep["trend_over_time"] is None
    assert len(rep["recommended_next_items"]) > 0


@pytest.mark.asyncio
async def test_test_finish_atomic_skill_ingestion_and_idempotency(async_client: AsyncClient, test_storage):
    user, token = await _create_test_user(test_storage, "test_finish_sync@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Setup verified career
    cid = uuid4()
    career = Career(
        id=cid,
        code="SWE",
        title="Software Engineer",
        cluster="Engineering",
        overview="Build software",
        dimension_weights={"skills": 30, "hours": 20},
        status="verified",
        created_at=datetime.now(timezone.utc),
    )
    test_storage["careers"][cid] = career

    # Setup verified questions in topic "DSA" (at least 6 required)
    q_ids = []
    for i in range(1, 7):
        qid = uuid4()
        diff = ((i - 1) % 3) + 1
        q = ModelTestQuestionBank(
            id=qid,
            type="skill",
            topic="DSA",
            subtopic="Binary Search" if i <= 3 else "Recursion",
            difficulty=diff,
            question_text=f"Sample Question {i}",
            options=[{"id": "a", "text": "Opt A"}, {"id": "b", "text": "Opt B"}],
            correct_option_id="a",
            explanation="Explanation text",
            source_note="Original question",
            status="verified",
            created_at=datetime.now(timezone.utc),
        )
        test_storage["test_question_banks"][qid] = q
        q_ids.append(qid)

    # Start test
    start_resp = await async_client.post(
        "/v1/tests/start",
        json={"career_id": str(cid), "type": "skill", "topic": "DSA"},
        headers=headers,
    )
    assert start_resp.status_code == 201
    test_id = start_resp.json()["test_id"]

    # Submit an answer
    ans_resp = await async_client.post(
        f"/v1/tests/{test_id}/answer",
        json={"question_id": str(start_resp.json()["current_question"]["id"]), "selected_option_id": "a"},
        headers=headers,
    )
    assert ans_resp.status_code == 200

    # Finish test
    finish_resp = await async_client.post(f"/v1/tests/{test_id}/finish", json={}, headers=headers)
    assert finish_resp.status_code == 200

    # Check that skill tracker was automatically updated for "dsa"!
    skills_resp = await async_client.get("/v1/skills", headers=headers)
    assert skills_resp.status_code == 200
    user_skills = skills_resp.json()["skills"]
    assert len(user_skills) == 1
    assert user_skills[0]["skill_slug"] == "dsa"
    skill_uuid = user_skills[0]["skill_id"]

    # Check report
    rep_resp = await async_client.get(f"/v1/skills/{skill_uuid}/report", headers=headers)
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    assert rep_data["evidence_count"] == 1
    assert any(sub in rep_data["strengths"] for sub in ["Binary Search", "Recursion"])

    # Double finish idempotency test
    finish_resp_again = await async_client.post(f"/v1/tests/{test_id}/finish", json={}, headers=headers)
    assert finish_resp_again.status_code == 200
    assert finish_resp_again.json()["status"] == "finished"

    # Verify no duplicate evidence was inserted
    rep_resp_again = await async_client.get(f"/v1/skills/{skill_uuid}/report", headers=headers)
    assert rep_resp_again.json()["evidence_count"] == 1


@pytest.mark.asyncio
async def test_no_direct_evidence_creation_endpoint(async_client: AsyncClient, test_storage):
    _, token = await _create_test_user(test_storage, "no_direct_ev@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempting to post to an evidence creation endpoint must fail
    resp = await async_client.post(
        "/v1/skills/evidence",
        json={"source_type": "test", "score": 100},
        headers=headers,
    )
    assert resp.status_code in [404, 405]
