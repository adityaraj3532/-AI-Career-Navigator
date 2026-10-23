from uuid import uuid4
import pytest
from httpx import AsyncClient


async def create_user_and_login(async_client: AsyncClient, email: str, password: str = "Password123!") -> str:
    signup_res = await async_client.post(
        "/v1/auth/signup",
        json={"email": email, "password": password, "education_level": "college"},
    )
    assert signup_res.status_code in [201, 409]

    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    return login_res.json()["access_token"]


@pytest.mark.asyncio
async def test_get_questions_returns_ordered_30_items(async_client: AsyncClient):
    token = await create_user_and_login(async_client, "questions_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/v1/assessment/questions", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["version_number"] == 1
    assert data["total_questions"] == 30
    assert len(data["questions"]) == 30

    orders = [q["question_order"] for q in data["questions"]]
    assert orders == list(range(1, 31))

    dimensions = {q["dimension"] for q in data["questions"]}
    assert dimensions == {"Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"}


@pytest.mark.asyncio
async def test_draft_save_and_resume_attempt(async_client: AsyncClient):
    token = await create_user_and_login(async_client, "draft_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch questions to get valid question IDs
    q_res = await async_client.get("/v1/assessment/questions", headers=headers)
    questions = q_res.json()["questions"]
    q1_id = questions[0]["id"]
    q2_id = questions[1]["id"]
    q3_id = questions[2]["id"]

    # 2. Get active draft attempt (should start empty)
    att_res1 = await async_client.get("/v1/assessment/attempt", headers=headers)
    assert att_res1.status_code == 200
    att1 = att_res1.json()
    assert att1["status"] == "draft"
    assert att1["answered_count"] == 0
    assert len(att1["answers"]) == 0
    attempt_id = att1["id"]

    # 3. Save draft answers for 3 questions
    save_payload = {
        "answers": [
            {"question_id": q1_id, "value": 5},
            {"question_id": q2_id, "value": 4},
            {"question_id": q3_id, "value": 3},
        ]
    }
    save_res = await async_client.post("/v1/assessment/answers", headers=headers, json=save_payload)
    assert save_res.status_code == 200
    save_data = save_res.json()
    assert save_data["id"] == attempt_id
    assert save_data["answered_count"] == 3
    assert len(save_data["answers"]) == 3

    # 4. Resume attempt later via GET /v1/assessment/attempt
    resume_res = await async_client.get("/v1/assessment/attempt", headers=headers)
    assert resume_res.status_code == 200
    resume_data = resume_res.json()
    assert resume_data["id"] == attempt_id
    assert resume_data["answered_count"] == 3

    saved_map = {a["question_id"]: a["value"] for a in resume_data["answers"]}
    assert saved_map[q1_id] == 5
    assert saved_map[q2_id] == 4
    assert saved_map[q3_id] == 3

    # 5. Upsert: change value of q1 from 5 to 2
    upsert_payload = {
        "answers": [
            {"question_id": q1_id, "value": 2},
        ]
    }
    upsert_res = await async_client.put("/v1/assessment/answers", headers=headers, json=upsert_payload)
    assert upsert_res.status_code == 200
    upsert_data = upsert_res.json()
    assert upsert_data["answered_count"] == 3  # Count stays 3

    new_saved_map = {a["question_id"]: a["value"] for a in upsert_data["answers"]}
    assert new_saved_map[q1_id] == 2  # Updated to 2


@pytest.mark.asyncio
async def test_invalid_answers_validation(async_client: AsyncClient):
    token = await create_user_and_login(async_client, "invalid_ans_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    q_res = await async_client.get("/v1/assessment/questions", headers=headers)
    q1_id = q_res.json()["questions"][0]["id"]

    # 1. Score out of range (< 1)
    res_low = await async_client.post(
        "/v1/assessment/answers",
        headers=headers,
        json={"answers": [{"question_id": q1_id, "value": 0}]},
    )
    assert res_low.status_code == 422
    assert "greater than or equal to 1" in res_low.text

    # 2. Score out of range (> 5)
    res_high = await async_client.post(
        "/v1/assessment/answers",
        headers=headers,
        json={"answers": [{"question_id": q1_id, "value": 6}]},
    )
    assert res_high.status_code == 422
    assert "less than or equal to 5" in res_high.text

    # 3. Non-existent question ID
    fake_qid = str(uuid4())
    res_fake = await async_client.post(
        "/v1/assessment/answers",
        headers=headers,
        json={"answers": [{"question_id": fake_qid, "value": 4}]},
    )
    assert res_fake.status_code == 400
    assert res_fake.json()["error"]["code"] == "INVALID_QUESTION_ID"

    # 4. Extra fields rejected (extra="forbid")
    res_extra = await async_client.post(
        "/v1/assessment/answers",
        headers=headers,
        json={"answers": [{"question_id": q1_id, "value": 4, "extra_field": "hack"}]},
    )
    assert res_extra.status_code == 422


@pytest.mark.asyncio
async def test_ownership_attempt_access_returns_404(async_client: AsyncClient):
    # User A creates an attempt
    token_a = await create_user_and_login(async_client, "user_a@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    att_res_a = await async_client.get("/v1/assessment/attempt", headers=headers_a)
    attempt_a_id = att_res_a.json()["id"]

    # User B logs in
    token_b = await create_user_and_login(async_client, "user_b@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B attempts to access User A's attempt ID directly
    unauthorized_res = await async_client.get(f"/v1/assessment/attempts/{attempt_a_id}", headers=headers_b)
    assert unauthorized_res.status_code == 404
    assert unauthorized_res.json()["error"]["code"] == "ATTEMPT_NOT_FOUND"
