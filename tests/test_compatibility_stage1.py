import math
import uuid
import pytest
from httpx import AsyncClient

from app.models.assessment import AssessmentResult
from app.models.career import Career
from app.models.profile import StudentProfile
from app.services.compatibility_service import (
    compute_career_compatibility,
    generate_inputs_hash,
)


@pytest.fixture
def sample_career() -> Career:
    return Career(
        id=uuid.uuid4(),
        code="CAREER-SDE",
        title="Software Development Engineer (SDE)",
        cluster="Technology & Engineering",
        demand="very_high",
        time_to_job_ready_months=48,
        entrance_difficulty="moderate",
        dimension_weights={"R": 40.0, "I": 95.0, "A": 50.0, "S": 35.0, "E": 45.0, "C": 75.0},
        required_skills=[
            {"name": "Data Structures & Algorithms", "level": "advanced"},
            {"name": "Backend Frameworks (FastAPI / Spring / Go)", "level": "advanced"},
            {"name": "Relational Databases & SQL", "level": "intermediate"},
        ],
        salary_ranges={
            "currency": "INR",
            "is_approximate": True,
            "as_of_year": 2026,
            "source_url": "https://example.com/salaries",
            "entry": {"min": 600000, "max": 1200000},
            "mid": {"min": 1400000, "max": 2800000},
            "senior": {"min": 3500000, "max": 7000000},
        },
        status="verified",
        source_url="https://example.com/sde",
    )


@pytest.fixture
def sample_assessment_result() -> AssessmentResult:
    return AssessmentResult(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        assessment_version_id=uuid.uuid4(),
        version=1,
        dimension_scores={"R": 45.0, "I": 90.0, "A": 55.0, "S": 30.0, "E": 40.0, "C": 70.0},
        holland_code="IRC",
        holland_code_label="The Systems Investigator",
        traits=["Analytical", "Methodical"],
        skills=["Python", "System Design"],
        career_suggestions=[],
        ai_explanation="Solid analytical and engineering orientation.",
    )


@pytest.fixture
def sample_profile() -> StudentProfile:
    return StudentProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Student",
        budget_level="medium",
        hours_available_per_week=20,
        subjects_of_interest=["Computer Science", "Mathematics", "Physics"],
        skills=[
            {"name": "Data Structures & Algorithms", "level": "advanced"},
            {"name": "Backend Frameworks", "level": "intermediate"},
            {"name": "Relational Databases", "level": "intermediate"},
        ],
    )


# ---------------------------------------------------------------------------
# Unit Tests: Pure Scoring Function
# ---------------------------------------------------------------------------

def test_scoring_all_five_factors_present(sample_career, sample_assessment_result, sample_profile):
    """Case 1: All 5 factors present. Weights (30, 25, 20, 15, 10). Re-normalized weights sum to 1.0."""
    score, completeness, excluded, breakdown, strengths, gaps = compute_career_compatibility(
        career=sample_career,
        assessment_result=sample_assessment_result,
        profile=sample_profile,
    )

    assert completeness == 100
    assert len(excluded) == 0
    assert len(breakdown) == 5

    # Check effective weights sum to 1.0
    effective_weights_sum = sum(b["effective_weight"] for b in breakdown.values())
    assert math.isclose(effective_weights_sum, 1.0, abs_tol=1e-4)

    assert 0 <= score <= 100
    assert len(strengths) > 0


def test_scoring_one_factor_missing_renormalization(sample_career, sample_assessment_result, sample_profile):
    """Case 2: 1 factor missing (budget missing). Remaining 4 weights re-normalise to sum to 1.0."""
    sample_profile.budget_level = None

    score, completeness, excluded, breakdown, strengths, gaps = compute_career_compatibility(
        career=sample_career,
        assessment_result=sample_assessment_result,
        profile=sample_profile,
    )

    assert completeness == 90  # 100 - 10
    assert "budget" in excluded
    assert breakdown["budget"]["status"] == "excluded"
    assert breakdown["budget"]["score"] is None
    assert breakdown["budget"]["effective_weight"] == 0.0

    present_eff_weights_sum = sum(
        b["effective_weight"] for b in breakdown.values() if b["status"] == "present"
    )
    assert math.isclose(present_eff_weights_sum, 1.0, abs_tol=1e-4)
    assert 0 <= score <= 100


def test_scoring_two_factors_missing(sample_career, sample_assessment_result, sample_profile):
    """Case 3: 2 factors missing (budget and hours missing). Effective weights sum to 1.0."""
    sample_profile.budget_level = None
    sample_profile.hours_available_per_week = None

    score, completeness, excluded, breakdown, strengths, gaps = compute_career_compatibility(
        career=sample_career,
        assessment_result=sample_assessment_result,
        profile=sample_profile,
    )

    assert completeness == 75  # 100 - (15 + 10)
    assert set(excluded) == {"hours", "budget"}

    present_eff_weights_sum = sum(
        b["effective_weight"] for b in breakdown.values() if b["status"] == "present"
    )
    assert math.isclose(present_eff_weights_sum, 1.0, abs_tol=1e-4)
    assert 0 <= score <= 100


def test_scoring_all_factors_missing(sample_career):
    """Case 4: All factors missing. Returns 0 score, 0 completeness, all excluded, never scores as 0 in weights."""
    score, completeness, excluded, breakdown, strengths, gaps = compute_career_compatibility(
        career=sample_career,
        assessment_result=None,
        profile=None,
    )

    assert score == 0
    assert completeness == 0
    assert len(excluded) == 5
    for b in breakdown.values():
        assert b["status"] == "excluded"
        assert b["score"] is None
        assert b["effective_weight"] == 0.0
    assert len(gaps) > 0


def test_scoring_boundary_zero_and_hundred(sample_career):
    """Case 5: Boundary conditions - 100% and 0%."""
    # Boundary 100%: perfect assessment match, expert skills, top subjects, max hours, high budget
    perfect_result = AssessmentResult(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        assessment_version_id=uuid.uuid4(),
        version=1,
        dimension_scores=sample_career.dimension_weights,  # Exact match
        holland_code="IRC",
        holland_code_label="Match",
        traits=[],
        skills=[],
        career_suggestions=[],
        ai_explanation="",
    )
    perfect_profile = StudentProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        budget_level="high",
        hours_available_per_week=40,
        subjects_of_interest=["Computer Science", "Mathematics", "Physics", "Coding"],
        skills=[
            {"name": "Data Structures & Algorithms", "level": "expert"},
            {"name": "Backend Frameworks (FastAPI / Spring / Go)", "level": "expert"},
            {"name": "Relational Databases & SQL", "level": "expert"},
        ],
    )

    score_100, comp_100, _, _, _, _ = compute_career_compatibility(
        career=sample_career,
        assessment_result=perfect_result,
        profile=perfect_profile,
    )
    assert score_100 == 100
    assert comp_100 == 100

    # Boundary 0%: user has 0 hours
    zero_profile = StudentProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        budget_level=None,
        hours_available_per_week=0,
        subjects_of_interest=[],
        skills=[],
    )
    score_0, comp_0, _, breakdown_0, _, _ = compute_career_compatibility(
        career=sample_career,
        assessment_result=None,
        profile=zero_profile,
    )
    assert score_0 == 0
    assert comp_0 == 15  # only hours present (base weight 15)
    assert breakdown_0["hours"]["score"] == 0


def test_inputs_hash_generation():
    """Inputs hash is deterministic, covers all relevant parameters, and is invariant to list order."""
    cid = uuid.uuid4()
    rid = uuid.uuid4()

    hash1 = generate_inputs_hash(
        career_id=cid,
        weights_version=1,
        assessment_result_id=rid,
        profile_budget="medium",
        profile_hours=20,
        profile_subjects=["Mathematics", "Physics"],
        profile_skills=[{"name": "Python", "level": "intermediate"}],
    )

    # Same data, different subject order
    hash2 = generate_inputs_hash(
        career_id=cid,
        weights_version=1,
        assessment_result_id=rid,
        profile_budget="medium",
        profile_hours=20,
        profile_subjects=["Physics", "Mathematics"],
        profile_skills=[{"name": "Python", "level": "intermediate"}],
    )
    assert hash1 == hash2

    # Changed hours -> hash changes
    hash3 = generate_inputs_hash(
        career_id=cid,
        weights_version=1,
        assessment_result_id=rid,
        profile_budget="medium",
        profile_hours=25,
        profile_subjects=["Mathematics", "Physics"],
        profile_skills=[{"name": "Python", "level": "intermediate"}],
    )
    assert hash1 != hash3


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def verify_test_careers(test_storage):
    """Mark seeded careers verified for integration tests."""
    for c in test_storage["careers"].values():
        c.status = "verified"


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


@pytest.mark.asyncio
async def test_profile_endpoints(async_client: AsyncClient):
    """Test GET /v1/profile and PUT /v1/profile."""
    token = await _signup_and_login(async_client, "student_prof@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # GET empty profile initially
    get_res = await async_client.get("/v1/profile", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["budget_level"] is None

    # PUT update profile
    update_data = {
        "name": "Alex Student",
        "budget_level": "medium",
        "hours_available_per_week": 18,
        "subjects_of_interest": ["Mathematics", "Computer Science"],
        "skills": [{"name": "Python", "level": "intermediate"}],
    }
    put_res = await async_client.put("/v1/profile", json=update_data, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["budget_level"] == "medium"
    assert put_res.json()["hours_available_per_week"] == 18
    assert put_res.json()["subjects_of_interest"] == ["Mathematics", "Computer Science"]


@pytest.mark.asyncio
async def test_compatibility_snapshot_creation_and_deduplication(async_client: AsyncClient, test_storage):
    """Test GET /v1/careers/{career_id}/compatibility generates snapshot and reuses it if inputs_hash is unchanged."""
    token = await _signup_and_login(async_client, "compat_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Find verified career
    career_res = await async_client.get("/v1/careers")
    assert career_res.status_code == 200
    career_id = career_res.json()["items"][0]["id"]

    # 1st request -> generates new snapshot
    resp1 = await async_client.get(f"/v1/careers/{career_id}/compatibility", headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    snapshot_id_1 = data1["id"]
    hash_1 = data1["inputs_hash"]
    assert data1["weights_version"] == 1
    assert data1["explanation_status"] == "pending"

    # 2nd request without changing inputs -> reuses existing snapshot (same ID)
    resp2 = await async_client.get(f"/v1/careers/{career_id}/compatibility", headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["id"] == snapshot_id_1
    assert data2["inputs_hash"] == hash_1

    # Update profile -> inputs_hash changes -> creates new snapshot
    await async_client.put(
        "/v1/profile",
        json={"budget_level": "high", "hours_available_per_week": 35},
        headers=headers,
    )
    resp3 = await async_client.get(f"/v1/careers/{career_id}/compatibility", headers=headers)
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["id"] != snapshot_id_1
    assert data3["inputs_hash"] != hash_1

    # History endpoint returns both snapshots ordered by created_at desc
    hist_resp = await async_client.get(f"/v1/careers/{career_id}/compatibility/history", headers=headers)
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["total_count"] >= 2
    assert hist_data["items"][0]["id"] == data3["id"]
    assert hist_data["items"][1]["id"] == snapshot_id_1


@pytest.mark.asyncio
async def test_shortlist_idempotency_limit_and_isolation(async_client: AsyncClient, test_storage):
    """Test shortlist add, delete, 20 max limit, idempotency, and user isolation."""
    # User 1
    u1_token = await _signup_and_login(async_client, "shortlist_u1@example.com")
    u1_headers = {"Authorization": f"Bearer {u1_token}"}

    # User 2
    u2_token = await _signup_and_login(async_client, "shortlist_u2@example.com")
    u2_headers = {"Authorization": f"Bearer {u2_token}"}

    careers_resp = await async_client.get("/v1/careers")
    careers = careers_resp.json()["items"]
    c1_id = careers[0]["id"]

    # 1. Add career 1 to User 1's shortlist
    add1 = await async_client.post(f"/v1/shortlist/{c1_id}", headers=u1_headers)
    assert add1.status_code == 200

    # 2. Idempotent re-add succeeds without duplicating
    add2 = await async_client.post(f"/v1/shortlist/{c1_id}", headers=u1_headers)
    assert add2.status_code == 200

    # User 1 sees 1 item
    list1 = await async_client.get("/v1/shortlist", headers=u1_headers)
    assert list1.status_code == 200
    assert list1.json()["total_count"] == 1

    # User 2 sees 0 items (strict ownership isolation)
    list2 = await async_client.get("/v1/shortlist", headers=u2_headers)
    assert list2.status_code == 200
    assert list2.json()["total_count"] == 0

    # 3. Idempotent delete
    del1 = await async_client.delete(f"/v1/shortlist/{c1_id}", headers=u1_headers)
    assert del1.status_code == 200
    del2 = await async_client.delete(f"/v1/shortlist/{c1_id}", headers=u1_headers)
    assert del2.status_code == 200

    list1_after = await async_client.get("/v1/shortlist", headers=u1_headers)
    assert list1_after.json()["total_count"] == 0

    # 4. Limit enforcement: mock or test 20 max limit
    created_ids = []
    for i in range(21):
        fake_id = uuid.uuid4()
        fake_career = Career(
            id=fake_id,
            code=f"CAREER-MOCK-{i}",
            title=f"Mock Career {i}",
            cluster="Technology",
            demand="moderate",
            status="verified",
            source_url="https://example.com",
            dimension_weights={"R": 50, "I": 50, "A": 50, "S": 50, "E": 50, "C": 50},
        )
        test_storage["careers"][fake_id] = fake_career
        created_ids.append(fake_id)

    # Add 20 careers
    for cid in created_ids[:20]:
        r = await async_client.post(f"/v1/shortlist/{cid}", headers=u1_headers)
        assert r.status_code == 200

    # Attempting 21st career is rejected with 400
    r_21 = await async_client.post(f"/v1/shortlist/{created_ids[20]}", headers=u1_headers)
    assert r_21.status_code == 400
    assert "limit of 20" in r_21.json()["error"]["message"].lower() or "limit of 20" in str(r_21.json()).lower()


@pytest.mark.asyncio
async def test_compare_endpoint(async_client: AsyncClient):
    """Test POST /v1/compare: accepts 2-4 distinct verified careers, deduplicates, rejects invalid counts."""
    careers_resp = await async_client.get("/v1/careers")
    careers = careers_resp.json()["items"]
    assert len(careers) >= 2
    c1, c2 = careers[0]["id"], careers[1]["id"]

    # 1. Less than 2 distinct IDs returns 400
    r_one = await async_client.post("/v1/compare", json={"career_ids": [c1, c1]})
    assert r_one.status_code == 400

    # 2. More than 4 distinct IDs returns 400
    fake_ids = [str(uuid.uuid4()) for _ in range(5)]
    r_five = await async_client.post("/v1/compare", json={"career_ids": fake_ids})
    assert r_five.status_code == 400

    # 3. Non-existent career ID returns 404
    r_404 = await async_client.post("/v1/compare", json={"career_ids": [c1, str(uuid.uuid4())]})
    assert r_404.status_code == 404

    # 4. Valid comparison with duplicates deduplicated: [c1, c2, c1] -> [c1, c2]
    r_valid = await async_client.post("/v1/compare", json={"career_ids": [c1, c2, c1]})
    assert r_valid.status_code == 200
    cmp_data = r_valid.json()
    assert len(cmp_data["careers"]) == 2
    assert cmp_data["careers"][0]["career_id"] == c1
    assert cmp_data["careers"][1]["career_id"] == c2
    assert cmp_data["ai_verdict"] is not None


@pytest.mark.asyncio
async def test_unverified_career_rejected(async_client: AsyncClient, test_storage):
    """Test unverified draft career returns 404 for compatibility and shortlist when drafts are forbidden."""
    draft_id = uuid.uuid4()
    draft_career = Career(
        id=draft_id,
        code="CAREER-DRAFT",
        title="Draft Career",
        cluster="Experimental",
        demand="moderate",
        status="draft",
        source_url="https://example.com/draft",
    )
    test_storage["careers"][draft_id] = draft_career

    token = await _signup_and_login(async_client, "draft_tester@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Shortlist draft -> 404
    r_short = await async_client.post(f"/v1/shortlist/{draft_id}", headers=headers)
    assert r_short.status_code == 404

    # Compatibility draft -> 404
    r_comp = await async_client.get(f"/v1/careers/{draft_id}/compatibility", headers=headers)
    assert r_comp.status_code == 404


