import pytest
from uuid import uuid4
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import User


@pytest.fixture
def auth_headers(test_storage):
    user_id = uuid4()
    user = User(
        id=user_id,
        email="interview_student@example.com",
        hashed_password="hashed_pw_test",
        education_level="College",
        is_active=True,
    )
    test_storage["users"][user_id] = user
    token = create_access_token(user_id=user_id, email=user.email, role=user.role)
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.fixture
def other_user_headers(test_storage):
    user_id = uuid4()
    user = User(
        id=user_id,
        email="other_student@example.com",
        hashed_password="hashed_pw_test2",
        education_level="College",
        is_active=True,
    )
    test_storage["users"][user_id] = user
    token = create_access_token(user_id=user_id, email=user.email, role=user.role)
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.fixture
def verified_questions(test_storage):
    """Mark draft questions as verified so start_interview can find them."""
    sde = next((c for c in test_storage["careers"].values() if c.code == "SOFTWARE_DEVELOPER"), None)
    for q in test_storage["interview_questions"].values():
        q.status = "verified"
    return sde


@pytest.mark.asyncio
async def test_start_interview_unauthorized(async_client: AsyncClient):
    res = await async_client.post("/v1/interviews/start", json={"type": "hr", "level": "beginner"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_start_interview_technical_requires_career(async_client: AsyncClient, auth_headers):
    headers, _ = auth_headers
    # Technical without career_id
    res = await async_client.post(
        "/v1/interviews/start",
        json={"type": "technical", "level": "beginner"},
        headers=headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_start_interview_extra_fields_forbidden(async_client: AsyncClient, auth_headers, verified_questions):
    headers, _ = auth_headers
    sde = verified_questions
    res = await async_client.post(
        "/v1/interviews/start",
        json={
            "career_id": str(sde.id),
            "type": "technical",
            "level": "beginner",
            "forbidden_extra": "hack",
        },
        headers=headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_start_interview_hides_criteria_and_sample_answers(
    async_client: AsyncClient, auth_headers, verified_questions
):
    headers, _ = auth_headers
    sde = verified_questions

    res = await async_client.post(
        "/v1/interviews/start",
        json={
            "career_id": str(sde.id),
            "type": "technical",
            "level": "beginner",
            "num_questions": 1,
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert data["status"] == "in_progress"
    current_q = data["current_question"]
    assert "question_text" in current_q
    # INVARIANT: Never send key_points or sample_answer before submission!
    assert "key_points" not in current_q
    assert "sample_answer" not in current_q


@pytest.mark.asyncio
async def test_one_active_session_conflict(
    async_client: AsyncClient, auth_headers, verified_questions
):
    headers, _ = auth_headers
    sde = verified_questions

    # Start first session
    res1 = await async_client.post(
        "/v1/interviews/start",
        json={"career_id": str(sde.id), "type": "technical", "level": "beginner", "num_questions": 1},
        headers=headers,
    )
    assert res1.status_code == 201

    # Attempting to start second session while first is active returns 409 Conflict
    res2 = await async_client.post(
        "/v1/interviews/start",
        json={"career_id": str(sde.id), "type": "technical", "level": "beginner", "num_questions": 1},
        headers=headers,
    )
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_submit_answer_scoring_and_sample_answer_revealed(
    async_client: AsyncClient, auth_headers, verified_questions
):
    headers, _ = auth_headers
    sde = verified_questions

    # Start session
    start_res = await async_client.post(
        "/v1/interviews/start",
        json={"career_id": str(sde.id), "type": "technical", "level": "beginner", "num_questions": 1},
        headers=headers,
    )
    start_data = start_res.json()
    session_id = start_data["session_id"]
    question_id = start_data["current_question"]["id"]

    # Submit answer
    ans_res = await async_client.post(
        f"/v1/interviews/{session_id}/answers",
        json={
            "session_question_id": question_id,
            "answer_text": "Arrays use contiguous memory giving O(1) random access, while linked lists use node pointers requiring O(N) sequential traversal.",
        },
        headers=headers,
    )
    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert "scores" in ans_data
    assert ans_data["scores"]["coverage_score"] > 0
    assert ans_data["scores"]["overall_score"] > 0
    # After submission: sample_answer is now revealed!
    assert ans_data["sample_answer"] is not None
    assert "practice_guidance_note" in ans_data
    assert ans_data["session_completed"] is True


@pytest.mark.asyncio
async def test_submit_answer_foreign_session_returns_404(
    async_client: AsyncClient, auth_headers, other_user_headers, verified_questions
):
    headers_user_a, _ = auth_headers
    headers_user_b, _ = other_user_headers
    sde = verified_questions

    # User A starts session
    start_res = await async_client.post(
        "/v1/interviews/start",
        json={"career_id": str(sde.id), "type": "technical", "level": "beginner", "num_questions": 1},
        headers=headers_user_a,
    )
    session_id = start_res.json()["session_id"]
    question_id = start_res.json()["current_question"]["id"]

    # User B attempts to submit answer to User A's session -> 404
    ans_res = await async_client.post(
        f"/v1/interviews/{session_id}/answers",
        json={"session_question_id": question_id, "answer_text": "Hacked answer from user b"},
        headers=headers_user_b,
    )
    assert ans_res.status_code == 404


@pytest.mark.asyncio
async def test_get_session_transcript_owner_vs_foreign(
    async_client: AsyncClient, auth_headers, other_user_headers, verified_questions
):
    headers_user_a, _ = auth_headers
    headers_user_b, _ = other_user_headers
    sde = verified_questions

    # Start session
    start_res = await async_client.post(
        "/v1/interviews/start",
        json={"career_id": str(sde.id), "type": "technical", "level": "beginner", "num_questions": 1},
        headers=headers_user_a,
    )
    session_id = start_res.json()["session_id"]

    # User A can view session
    res_a = await async_client.get(f"/v1/interviews/{session_id}", headers=headers_user_a)
    assert res_a.status_code == 200
    assert res_a.json()["session_id"] == session_id

    # User B cannot view session -> 404
    res_b = await async_client.get(f"/v1/interviews/{session_id}", headers=headers_user_b)
    assert res_b.status_code == 404


@pytest.mark.asyncio
async def test_get_analytics_insufficient_data(async_client: AsyncClient, auth_headers):
    headers, _ = auth_headers
    res = await async_client.get("/v1/interviews/analytics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_sufficient_data"] is False
    assert data["trends"] is None
    assert "At least 2 completed sessions" in data["message"]


@pytest.mark.asyncio
async def test_get_analytics_with_multiple_completed_sessions(
    async_client: AsyncClient, auth_headers, verified_questions
):
    headers, _ = auth_headers
    sde = verified_questions

    # Complete Session 1
    s1_res = await async_client.post(
        "/v1/interviews/start",
        json={"career_id": str(sde.id), "type": "technical", "level": "beginner", "num_questions": 1},
        headers=headers,
    )
    s1_id = s1_res.json()["session_id"]
    q1_id = s1_res.json()["current_question"]["id"]
    await async_client.post(
        f"/v1/interviews/{s1_id}/answers",
        json={"session_question_id": q1_id, "answer_text": "Arrays contiguous memory O(1) random access."},
        headers=headers,
    )

    # Complete Session 2
    s2_res = await async_client.post(
        "/v1/interviews/start",
        json={"career_id": str(sde.id), "type": "technical", "level": "beginner", "num_questions": 1},
        headers=headers,
    )
    s2_id = s2_res.json()["session_id"]
    q2_id = s2_res.json()["current_question"]["id"]
    await async_client.post(
        f"/v1/interviews/{s2_id}/answers",
        json={"session_question_id": q2_id, "answer_text": "Arrays allocate memory contiguously with cache locality, whereas linked lists use nodes."},
        headers=headers,
    )

    # Analytics now has sufficient data!
    an_res = await async_client.get("/v1/interviews/analytics?type=technical", headers=headers)
    assert an_res.status_code == 200
    an_data = an_res.json()
    assert an_data["has_sufficient_data"] is True
    assert an_data["total_completed"] >= 2
    assert "coverage" in an_data["trends"]
    assert "depth" in an_data["trends"]
    assert "structure" in an_data["trends"]
    assert "overall" in an_data["trends"]
    assert an_data["weakest_dimension"] is not None
    assert an_data["strongest_dimension"] is not None


@pytest.mark.asyncio
async def test_interview_history_pagination(
    async_client: AsyncClient, auth_headers, verified_questions
):
    headers, _ = auth_headers
    sde = verified_questions

    # Start and complete session
    s_res = await async_client.post(
        "/v1/interviews/start",
        json={"career_id": str(sde.id), "type": "technical", "level": "beginner", "num_questions": 1},
        headers=headers,
    )
    sid = s_res.json()["session_id"]
    qid = s_res.json()["current_question"]["id"]
    await async_client.post(
        f"/v1/interviews/{sid}/answers",
        json={"session_question_id": qid, "answer_text": "Completed answer."},
        headers=headers,
    )

    # Query history
    h_res = await async_client.get("/v1/interviews/history?page=1&page_size=5", headers=headers)
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["total"] >= 1
    assert len(h_data["items"]) >= 1
    assert h_data["items"][0]["status"] == "completed"
