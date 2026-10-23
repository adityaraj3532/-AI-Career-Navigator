import json
import uuid
import pytest
from httpx import AsyncClient

from app.services.scoring_service import (
    calculate_career_similarity,
    compute_riasec_scores,
    derive_holland_code,
    derive_traits_and_skills,
    map_streams_for_grade_11_12,
    rank_careers,
)


# =====================================================================
# 1. Deterministic Scoring Unit Tests (6 Fixed Cases + Math Invariants)
# =====================================================================

def test_scoring_case_1_all_ones():
    """All 1s: non-reversed items contribute 1, reversed items contribute 5."""
    # 30 questions total, 5 per dimension
    questions = [
        {"question_order": i, "dimension": d, "reverse_scored": (i % 5 == 0)}
        for idx, d in enumerate(["R", "I", "A", "S", "E", "C"])
        for i in range(idx * 5 + 1, idx * 5 + 6)
    ]
    answers = {q["question_order"]: 1 for q in questions}
    scores = compute_riasec_scores(answers, questions)

    # 4 non-reversed (1 each = 4), 1 reversed (6 - 1 = 5) -> raw sum = 9
    # normalized = ((9 - 5) / 20) * 100 = 20.0
    for dim in ["R", "I", "A", "S", "E", "C"]:
        assert scores[dim] == 20.0

    # Tied scores broken by canonical order R -> I -> A -> S -> E -> C
    code, label = derive_holland_code(scores)
    assert code == "RIA"


def test_scoring_case_2_all_fives():
    """All 5s: non-reversed items contribute 5, reversed items contribute 1."""
    questions = [
        {"question_order": i, "dimension": d, "reverse_scored": (i % 5 == 0)}
        for idx, d in enumerate(["R", "I", "A", "S", "E", "C"])
        for i in range(idx * 5 + 1, idx * 5 + 6)
    ]
    answers = {q["question_order"]: 5 for q in questions}
    scores = compute_riasec_scores(answers, questions)

    # 4 non-reversed (5 each = 20), 1 reversed (6 - 5 = 1) -> raw sum = 21
    # normalized = ((21 - 5) / 20) * 100 = 80.0
    for dim in ["R", "I", "A", "S", "E", "C"]:
        assert scores[dim] == 80.0

    code, _ = derive_holland_code(scores)
    assert code == "RIA"


def test_scoring_case_3_all_threes_neutral():
    """All 3s: non-reversed (3), reversed (6 - 3 = 3) -> raw sum = 15, normalized = 50.0."""
    questions = [
        {"question_order": i, "dimension": d, "reverse_scored": (i % 2 == 0)}
        for idx, d in enumerate(["R", "I", "A", "S", "E", "C"])
        for i in range(idx * 5 + 1, idx * 5 + 6)
    ]
    answers = {q["question_order"]: 3 for q in questions}
    scores = compute_riasec_scores(answers, questions)

    for dim in ["R", "I", "A", "S", "E", "C"]:
        assert scores[dim] == 50.0

    code, _ = derive_holland_code(scores)
    assert code == "RIA"


def test_scoring_case_4_distinct_high_dimensions():
    """Investigative, Artistic, and Social dominate."""
    questions = [
        {"question_order": 1, "dimension": "I", "reverse_scored": False},
        {"question_order": 2, "dimension": "I", "reverse_scored": False},
        {"question_order": 3, "dimension": "A", "reverse_scored": False},
        {"question_order": 4, "dimension": "S", "reverse_scored": False},
        {"question_order": 5, "dimension": "R", "reverse_scored": False},
        {"question_order": 6, "dimension": "E", "reverse_scored": False},
        {"question_order": 7, "dimension": "C", "reverse_scored": False},
    ]
    answers = {1: 5, 2: 5, 3: 4, 4: 4, 5: 1, 6: 2, 7: 1}
    scores = compute_riasec_scores(answers, questions)

    code, label = derive_holland_code(scores)
    assert code.startswith("I")
    assert "A" in code
    assert "S" in code
    traits, skills = derive_traits_and_skills(code)
    assert len(traits) > 0
    assert len(skills) > 0


def test_scoring_case_5_reverse_scoring_precision():
    """Verify that reverse-scored item accurately inverts scale."""
    q_standard = [{"question_order": 1, "dimension": "R", "reverse_scored": False}]
    q_reverse = [{"question_order": 1, "dimension": "R", "reverse_scored": True}]

    # Raw 5 on standard -> 100.0; Raw 5 on reversed -> 0.0
    assert compute_riasec_scores({1: 5}, q_standard)["R"] == 100.0
    assert compute_riasec_scores({1: 5}, q_reverse)["R"] == 0.0

    # Raw 1 on standard -> 0.0; Raw 1 on reversed -> 100.0
    assert compute_riasec_scores({1: 1}, q_standard)["R"] == 0.0
    assert compute_riasec_scores({1: 1}, q_reverse)["R"] == 100.0


def test_scoring_case_6_canonical_tie_breaking():
    """Explicitly verify tie-break ordering when multiple dimensions have equal high scores."""
    scores = {"R": 75.0, "I": 75.0, "A": 75.0, "S": 75.0, "E": 75.0, "C": 75.0}
    code, _ = derive_holland_code(scores)
    assert code == "RIA"

    # When S, E, C are 90 and R, I, A are 60:
    scores_sec = {"R": 60.0, "I": 60.0, "A": 60.0, "S": 90.0, "E": 90.0, "C": 90.0}
    code_sec, _ = derive_holland_code(scores_sec)
    assert code_sec == "SEC"


# =====================================================================
# 2. Vector Similarity & Career Ranking Unit Tests
# =====================================================================

def test_career_similarity_exact_match():
    user = {"R": 10.0, "I": 90.0, "A": 70.0, "S": 50.0, "E": 30.0, "C": 60.0}
    career = {"R": 10.0, "I": 90.0, "A": 70.0, "S": 50.0, "E": 30.0, "C": 60.0}
    sim = calculate_career_similarity(user, career)
    assert sim == 1.0


def test_career_ranking_deterministic_tie_breaker():
    user = {"R": 50.0, "I": 50.0, "A": 50.0, "S": 50.0, "E": 50.0, "C": 50.0}
    careers = [
        {
            "id": uuid.uuid4(),
            "code": "B_CAREER",
            "title": "Beta Career",
            "cluster": "Tech",
            "overview": "Overview B",
            "dimension_weights": {"R": 50, "I": 50, "A": 50, "S": 50, "E": 50, "C": 50},
        },
        {
            "id": uuid.uuid4(),
            "code": "A_CAREER",
            "title": "Alpha Career",
            "cluster": "Tech",
            "overview": "Overview A",
            "dimension_weights": {"R": 50, "I": 50, "A": 50, "S": 50, "E": 50, "C": 50},
        },
    ]
    ranked = rank_careers(user, careers, top_n=2)
    # Both have identical similarity (1.0). Alpha Career must come first due to alphabetical title sort
    assert ranked[0]["title"] == "Alpha Career"
    assert ranked[1]["title"] == "Beta Career"


def test_grade_11_12_stream_mapping():
    pcm_scores = {"R": 85.0, "I": 95.0, "A": 20.0, "S": 30.0, "E": 40.0, "C": 50.0}
    streams = map_streams_for_grade_11_12(pcm_scores, "IRC")
    assert any("Science (PCM" in s for s in streams)

    arts_scores = {"R": 10.0, "I": 30.0, "A": 95.0, "S": 85.0, "E": 50.0, "C": 20.0}
    streams_arts = map_streams_for_grade_11_12(arts_scores, "ASE")
    assert any("Humanities" in s for s in streams_arts)


# =====================================================================
# 3. Assessment API End-to-End Tests (Incomplete, Submit, Idempotency, Retake, Ownership)
# =====================================================================

async def _register_and_login(client: AsyncClient, email: str, ed_level: str = "class_11_12") -> str:
    signup_res = await client.post(
        "/v1/auth/signup",
        json={"email": email, "password": "SecurePassword123!", "education_level": ed_level},
    )
    assert signup_res.status_code == 201

    login_res = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    return login_res.json()["access_token"]


@pytest.mark.asyncio
async def test_submit_incomplete_assessment_returns_400(async_client: AsyncClient):
    token = await _register_and_login(async_client, "incomplete@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Start attempt
    att_res = await async_client.get("/v1/assessment/attempt", headers=headers)
    assert att_res.status_code == 200

    # Answer only 1 question
    q_res = await async_client.get("/v1/assessment/questions", headers=headers)
    questions = q_res.json()["questions"]
    first_q_id = questions[0]["id"]

    save_res = await async_client.post(
        "/v1/assessment/answers",
        headers=headers,
        json={"answers": [{"question_id": first_q_id, "value": 4}]},
    )
    assert save_res.status_code == 200

    # Submit without answering all 30
    sub_res = await async_client.post("/v1/assessment/submit", headers=headers, json={})
    assert sub_res.status_code == 400
    sub_data = sub_res.json()
    assert sub_data["error"]["code"] == "INCOMPLETE_ASSESSMENT"
    assert sub_data["error"]["details"]["missing_count"] == 29
    assert len(sub_data["error"]["details"]["missing_question_ids"]) == 29


@pytest.mark.asyncio
async def test_full_assessment_flow_submit_idempotent_and_retake(
    async_client: AsyncClient,
    test_storage,
):
    # Verify careers in test_storage so they can be matched
    for c in test_storage["careers"].values():
        c.status = "verified"

    token = await _register_and_login(async_client, "completer@example.com", "class_11_12")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch questions
    q_res = await async_client.get("/v1/assessment/questions", headers=headers)
    questions = q_res.json()["questions"]
    assert len(questions) == 30

    # 2. Answer all 30 questions
    answers = [{"question_id": q["id"], "value": 4 if q["dimension"] in ("I", "A", "S") else 2} for q in questions]
    save_res = await async_client.post("/v1/assessment/answers", headers=headers, json={"answers": answers})
    assert save_res.status_code == 200
    assert save_res.json()["answered_count"] == 30

    # 3. Submit
    sub_res = await async_client.post("/v1/assessment/submit", headers=headers, json={})
    assert sub_res.status_code == 200
    data = sub_res.json()

    assert data["version"] == 1
    assert data["holland_code"] != ""
    assert data["holland_code_label"] != ""
    assert len(data["traits"]) > 0
    assert len(data["skills"]) > 0
    # Class 11/12 must receive recommended streams
    assert data["recommended_streams"] is not None
    assert len(data["recommended_streams"]) > 0
    # Suggestions
    assert len(data["career_suggestions"]) == 3
    for sug in data["career_suggestions"]:
        assert sug["title"] != ""
        assert sug["similarity_score"] > 0
        assert sug["reason"] != ""
    assert "guidance" in data["disclaimer_note"].lower()

    first_result_id = data["id"]

    # 4. Idempotent re-submission on same attempt returns exact same result
    sub_again = await async_client.post("/v1/assessment/submit", headers=headers, json={})
    assert sub_again.status_code == 200
    assert sub_again.json()["id"] == first_result_id
    assert sub_again.json()["version"] == 1

    # 5. Fetch latest result endpoint
    latest_res = await async_client.get("/v1/assessment/results/latest", headers=headers)
    assert latest_res.status_code == 200
    assert latest_res.json()["id"] == first_result_id

    # 6. Fetch all results endpoint
    all_res = await async_client.get("/v1/assessment/results", headers=headers)
    assert all_res.status_code == 200
    assert len(all_res.json()) == 1

    # 7. Retake assessment (starts version 2)
    # Start a new attempt
    new_att_res = await async_client.get("/v1/assessment/attempt", headers=headers)
    assert new_att_res.status_code == 200
    new_att_id = new_att_res.json()["id"]

    # Answer all 30 questions differently
    new_answers = [{"question_id": q["id"], "value": 5 if q["dimension"] == "R" else 1} for q in questions]
    await async_client.post("/v1/assessment/answers", headers=headers, json={"answers": new_answers})

    # Submit retake
    retake_sub = await async_client.post(
        "/v1/assessment/submit",
        headers=headers,
        json={"attempt_id": new_att_id},
    )
    assert retake_sub.status_code == 200
    retake_data = retake_sub.json()
    assert retake_data["version"] == 2
    assert retake_data["id"] != first_result_id

    # Check that all results endpoint now returns both versions
    all_res_after = await async_client.get("/v1/assessment/results", headers=headers)
    assert len(all_res_after.json()) == 2


@pytest.mark.asyncio
async def test_draft_careers_excluded_when_not_allowed(
    async_client: AsyncClient,
    test_storage,
    monkeypatch,
):
    # Ensure all careers are "draft"
    for c in test_storage["careers"].values():
        c.status = "draft"

    token = await _register_and_login(async_client, "draftcheck@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    q_res = await async_client.get("/v1/assessment/questions", headers=headers)
    questions = q_res.json()["questions"]
    answers = [{"question_id": q["id"], "value": 3} for q in questions]
    await async_client.post("/v1/assessment/answers", headers=headers, json={"answers": answers})

    # When all careers are draft and allow_drafts is false -> 503 NO_AVAILABLE_CAREERS
    sub_res = await async_client.post("/v1/assessment/submit", headers=headers, json={})
    assert sub_res.status_code == 503
    assert sub_res.json()["error"]["code"] == "NO_AVAILABLE_CAREERS"


@pytest.mark.asyncio
async def test_ownership_isolation(async_client: AsyncClient, test_storage):
    for c in test_storage["careers"].values():
        c.status = "verified"

    token_a = await _register_and_login(async_client, "user_a@example.com")
    token_b = await _register_and_login(async_client, "user_b@example.com")

    # User A starts and completes attempt
    h_a = {"Authorization": f"Bearer {token_a}"}
    h_b = {"Authorization": f"Bearer {token_b}"}

    q_res = await async_client.get("/v1/assessment/questions", headers=h_a)
    questions = q_res.json()["questions"]
    answers = [{"question_id": q["id"], "value": 4} for q in questions]
    await async_client.post("/v1/assessment/answers", headers=h_a, json={"answers": answers})
    sub_res = await async_client.post("/v1/assessment/submit", headers=h_a, json={})
    assert sub_res.status_code == 200
    res_a = sub_res.json()
    attempt_a_id = res_a["attempt_id"]
    result_a_id = res_a["id"]

    # User B tries to view User A's attempt -> 404
    att_res_b = await async_client.get(f"/v1/assessment/attempts/{attempt_a_id}", headers=h_b)
    assert att_res_b.status_code == 404

    # User B tries to view User A's result -> 404
    res_b = await async_client.get(f"/v1/assessment/results/{result_a_id}", headers=h_b)
    assert res_b.status_code == 404


@pytest.mark.asyncio
async def test_ai_unknown_career_id_triggers_deterministic_fallback(
    async_client: AsyncClient,
    test_storage,
    monkeypatch,
):
    from app.llm.gateway import LLMGateway
    from app.llm.provider import MockLLMProvider
    from app.services.assessment_service import AssessmentService

    for c in test_storage["careers"].values():
        c.status = "verified"

    # Mock provider returns valid JSON but with a bogus unknown career ID
    bogus_id = str(uuid.uuid4())
    fake_response = json.dumps({
        "summary_explanation": "Invented AI overview.",
        "career_reasons": {
            bogus_id: "Bogus reason referencing unknown career ID."
        }
    })
    mock_provider = MockLLMProvider(responses=[fake_response])
    gateway = LLMGateway(provider=mock_provider)

    # Monkeypatch AssessmentService to use this gateway
    orig_init = AssessmentService.__init__

    def custom_init(self, session, **kwargs):
        orig_init(self, session, gateway=gateway)

    monkeypatch.setattr(AssessmentService, "__init__", custom_init)

    token = await _register_and_login(async_client, "fallback_test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    q_res = await async_client.get("/v1/assessment/questions", headers=headers)
    questions = q_res.json()["questions"]
    answers = [{"question_id": q["id"], "value": 4} for q in questions]
    await async_client.post("/v1/assessment/answers", headers=headers, json={"answers": answers})

    sub_res = await async_client.post("/v1/assessment/submit", headers=headers, json={})
    assert sub_res.status_code == 200
    data = sub_res.json()

    # Telemetry should confirm fallback_used was True
    assert gateway.last_telemetry is not None
    assert gateway.last_telemetry.fallback_used is True

    # Result reasons should be populated from the deterministic fallback
    for sug in data["career_suggestions"]:
        assert "outstanding match" in sug["reason"] or "profile" in sug["reason"]


@pytest.mark.asyncio
async def test_assessment_qa_and_choose_career(
    async_client: AsyncClient,
    test_storage,
):
    for c in test_storage["careers"].values():
        c.status = "verified"

    # User A registers, takes assessment, submits
    token_a = await _register_and_login(async_client, "qa_user_a@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    q_res = await async_client.get("/v1/assessment/questions", headers=headers_a)
    questions = q_res.json()["questions"]
    answers = [{"question_id": q["id"], "value": 5} for q in questions]
    await async_client.post("/v1/assessment/answers", headers=headers_a, json={"answers": answers})

    sub_res = await async_client.post("/v1/assessment/submit", headers=headers_a, json={})
    assert sub_res.status_code == 200
    res_data = sub_res.json()
    result_id = res_data["id"]
    chosen_career_id = res_data["career_suggestions"][0]["career_id"]

    # 1. Ask in-scope question
    qa_payload = {
        "question": "Why is Software Development Engineer recommended for me?",
        "conversation_history": [],
    }
    qa_res = await async_client.post(
        f"/v1/assessment/results/{result_id}/ask",
        headers=headers_a,
        json=qa_payload,
    )
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert "answer" in qa_data
    assert len(qa_data["answer"]) > 0

    # 2. User B tries to ask on User A's result -> 404 (Ownership check)
    token_b = await _register_and_login(async_client, "qa_user_b@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    qa_res_b = await async_client.post(
        f"/v1/assessment/results/{result_id}/ask",
        headers=headers_b,
        json=qa_payload,
    )
    assert qa_res_b.status_code == 404

    # 3. Choose Career from result
    choose_payload = {"career_id": chosen_career_id}
    choose_res = await async_client.post(
        f"/v1/assessment/results/{result_id}/choose",
        headers=headers_a,
        json=choose_payload,
    )
    assert choose_res.status_code == 200
    choose_data = choose_res.json()
    assert choose_data["career_id"] == chosen_career_id
    assert "successfully chosen" in choose_data["message"].lower()

    # 4. Choosing unknown career -> 404
    choose_bad_res = await async_client.post(
        f"/v1/assessment/results/{result_id}/choose",
        headers=headers_a,
        json={"career_id": str(uuid.uuid4())},
    )
    assert choose_bad_res.status_code == 404

    # 5. User B tries to choose on User A's result -> 404
    choose_b_res = await async_client.post(
        f"/v1/assessment/results/{result_id}/choose",
        headers=headers_b,
        json=choose_payload,
    )
    assert choose_b_res.status_code == 404


