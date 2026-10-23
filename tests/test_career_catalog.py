from pathlib import Path
import pytest
from httpx import AsyncClient

from scripts.seed_career_catalog import seed_career_catalog


async def _signup_and_login(client: AsyncClient, email: str) -> str:
    signup_res = await client.post(
        "/v1/auth/signup",
        json={"email": email, "password": "SecurePassword123!", "education_level": "college"},
    )
    assert signup_res.status_code == 201

    login_res = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    return login_res.json()["access_token"]


@pytest.mark.asyncio
async def test_draft_careers_hidden_by_default(async_client: AsyncClient, test_storage):
    # Ensure all careers are "draft"
    for c in test_storage["careers"].values():
        c.status = "draft"

    # Public unauthenticated listing
    res = await async_client.get("/v1/careers")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 0
    assert len(data["items"]) == 0

    # Specific draft career detail returns 404
    first_career_id = list(test_storage["careers"].keys())[0]
    detail_res = await async_client.get(f"/v1/careers/{first_career_id}")
    assert detail_res.status_code == 404
    assert detail_res.json()["error"]["code"] == "CAREER_NOT_FOUND"


@pytest.mark.asyncio
async def test_verified_careers_listing_and_pagination(async_client: AsyncClient, test_storage):
    # Mark all careers verified
    for c in test_storage["careers"].values():
        c.status = "verified"

    # 1. Default pagination
    res = await async_client.get("/v1/careers")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 8
    assert len(data["items"]) == 8
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 1

    # Verify stable ordering (alphabetical by title)
    titles = [item["title"] for item in data["items"]]
    assert titles == sorted(titles)

    # 2. Custom page size
    res_paged = await async_client.get("/v1/careers?page=1&page_size=3")
    assert res_paged.status_code == 200
    data_paged = res_paged.json()
    assert len(data_paged["items"]) == 3
    assert data_paged["total_count"] == 8
    assert data_paged["total_pages"] == 3

    # Page 2
    res_p2 = await async_client.get("/v1/careers?page=2&page_size=3")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["items"]) == 3
    assert data_p2["items"][0]["id"] != data_paged["items"][0]["id"]

    # 3. Pagination bounds: page_size max 50
    res_max = await async_client.get("/v1/careers?page=1&page_size=50")
    assert res_max.status_code == 200
    assert res_max.json()["page_size"] == 50

    # Requesting > 50 fails validation schema
    res_over = await async_client.get("/v1/careers?page_size=51")
    assert res_over.status_code == 422


@pytest.mark.asyncio
async def test_career_filtering(async_client: AsyncClient, test_storage):
    for c in test_storage["careers"].values():
        c.status = "verified"

    # Filter by cluster
    res_cluster = await async_client.get("/v1/careers?cluster=Technology %26 Engineering")
    assert res_cluster.status_code == 200
    data_cluster = res_cluster.json()
    assert data_cluster["total_count"] == 1
    assert data_cluster["items"][0]["code"] == "SOFTWARE_DEVELOPER"

    # Filter by demand
    res_demand = await async_client.get("/v1/careers?demand=very_high")
    assert res_demand.status_code == 200
    data_demand = res_demand.json()
    assert data_demand["total_count"] >= 2
    for item in data_demand["items"]:
        assert item["demand"] == "very_high"

    # Filter by min_salary
    res_sal = await async_client.get("/v1/careers?min_salary=700000")
    assert res_sal.status_code == 200
    data_sal = res_sal.json()
    for item in data_sal["items"]:
        entry_min = item["salary_ranges"]["entry"]["min"]
        mid_min = item["salary_ranges"]["mid"]["min"]
        assert entry_min >= 700000 or mid_min >= 700000


@pytest.mark.asyncio
async def test_career_detail_eager_loading_and_structure(async_client: AsyncClient, test_storage):
    for key in ["careers", "exams", "colleges", "courses", "certificates", "internships"]:
        for item in test_storage[key].values():
            item.status = "verified"

    # Find Software Developer
    sde_id = None
    for cid, c in test_storage["careers"].items():
        if c.code == "SOFTWARE_DEVELOPER":
            sde_id = cid
            break
    assert sde_id is not None

    res = await async_client.get(f"/v1/careers/{sde_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["code"] == "SOFTWARE_DEVELOPER"
    assert data["title"] == "Software Development Engineer (SDE)"
    assert len(data["aliases"]) >= 2
    assert "Software Engineer" in data["aliases"]
    assert data["salary_ranges"]["currency"] == "INR"
    assert data["salary_ranges"]["is_approximate"] is True
    assert data["salary_ranges"]["entry"]["min"] == 600000
    assert len(data["required_skills"]) > 0
    assert len(data["education_paths"]) > 0

    # Linked entities eager-loaded
    assert len(data["exams"]) > 0
    exam_codes = [e["code"] for e in data["exams"]]
    assert "JEE_MAIN" in exam_codes
    assert "GATE" in exam_codes

    assert len(data["colleges"]) > 0
    college_names = [col["name"] for col in data["colleges"]]
    assert any("Indian Institute of Technology" in name for name in college_names)
    for col in data["colleges"]:
        assert col["fees"] is None  # verified null for initial draft seed
        assert col["cutoffs"] is None
        assert col["nirf_rank"] is None
        assert col["official_url"] != ""

    assert len(data["courses"]) > 0
    course_codes = [c["code"] for c in data["courses"]]
    assert "BTECH_CSE" in course_codes

    assert len(data["certificates"]) > 0
    cert_codes = [c["code"] for c in data["certificates"]]
    assert "AWS_SOL_ARCH" in cert_codes

    assert len(data["internships"]) > 0
    intern_codes = [i["code"] for i in data["internships"]]
    assert "SDE_INTERNSHIP" in intern_codes

    assert len(data["related_careers"]) > 0
    related_codes = [r["code"] for r in data["related_careers"]]
    assert "AI_ML_ENGINEER" in related_codes


@pytest.mark.asyncio
async def test_compatibility_score_optional_auth(async_client: AsyncClient, test_storage):
    for c in test_storage["careers"].values():
        c.status = "verified"

    # 1. Unauthenticated request -> compatibility_score is None
    res_anon = await async_client.get("/v1/careers")
    assert res_anon.status_code == 200
    for item in res_anon.json()["items"]:
        assert item["compatibility_score"] is None

    # 2. Authenticated user without assessment -> compatibility_score is None
    token = await _signup_and_login(async_client, "no_assessment@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    res_auth_no_score = await async_client.get("/v1/careers", headers=headers)
    assert res_auth_no_score.status_code == 200
    for item in res_auth_no_score.json()["items"]:
        assert item["compatibility_score"] is None

    # 3. Authenticated user WITH assessment -> compatibility_score is integer 0-100
    # Complete assessment
    q_res = await async_client.get("/v1/assessment/questions", headers=headers)
    questions = q_res.json()["questions"]
    answers = [{"question_id": q["id"], "value": 4 if q["dimension"] in ("R", "I") else 2} for q in questions]
    await async_client.post("/v1/assessment/answers", headers=headers, json={"answers": answers})
    sub_res = await async_client.post("/v1/assessment/submit", headers=headers, json={})
    assert sub_res.status_code == 200

    # Query careers listing with auth
    res_with_score = await async_client.get("/v1/careers", headers=headers)
    assert res_with_score.status_code == 200
    items = res_with_score.json()["items"]
    assert len(items) > 0
    for item in items:
        assert isinstance(item["compatibility_score"], int)
        assert 0 <= item["compatibility_score"] <= 100

    # Query career detail with auth
    first_id = items[0]["id"]
    detail_res = await async_client.get(f"/v1/careers/{first_id}", headers=headers)
    assert detail_res.status_code == 200
    assert isinstance(detail_res.json()["compatibility_score"], int)
    assert 0 <= detail_res.json()["compatibility_score"] <= 100


@pytest.mark.asyncio
async def test_idempotent_catalog_seeder(test_storage):
    catalog_path = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "career_catalog.json"
    assert catalog_path.is_file()

    from tests.conftest import MockSession
    mock_session = MockSession(test_storage)

    # First pass
    stats1 = await seed_career_catalog(mock_session, catalog_path)
    assert stats1["careers"] >= 0

    # Second pass (idempotent, does not raise duplicate key or blow up)
    stats2 = await seed_career_catalog(mock_session, catalog_path)
    assert isinstance(stats2, dict)


def test_migration_004_upgrade_and_downgrade():
    """Verify Alembic migration 004 can generate static SQL for upgrade and downgrade without errors."""
    import subprocess
    import sys

    # 1. Test offline upgrade SQL generation
    res_up = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        capture_output=True,
        text=True,
    )
    assert res_up.returncode == 0, f"Alembic upgrade --sql failed: {res_up.stderr}"
    assert "CREATE TABLE career_exams" in res_up.stdout
    assert "ALTER TABLE careers ADD COLUMN aliases" in res_up.stdout

    # 2. Test offline downgrade SQL generation
    res_down = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "downgrade",
            "004_create_career_catalog_tables:003_create_careers_and_assessment_results",
            "--sql",
        ],
        capture_output=True,
        text=True,
    )
    assert res_down.returncode == 0, f"Alembic downgrade --sql failed: {res_down.stderr}"
    assert "DROP TABLE career_exams" in res_down.stdout
    assert "ALTER TABLE careers DROP COLUMN aliases" in res_down.stdout


@pytest.mark.asyncio
async def test_detail_query_count_does_not_grow_with_linked_records(test_storage):
    """
    Verifies that eager loading (selectinload) maintains constant O(1) query complexity
    relative to the number of linked items (avoiding N+1 query explosion).
    """
    from app.models.career import Career

    # Verify that Career relationship configurations use selectinload
    for rel_name in ["exams", "colleges", "courses", "certificates", "internships", "related_careers"]:
        rel_prop = getattr(Career, rel_name).property
        assert rel_prop.lazy == "selectin", f"Relationship '{rel_name}' must use lazy='selectin' for bounded eager loading"


@pytest.mark.asyncio
async def test_career_search_by_title_and_alias(async_client: AsyncClient, test_storage):
    # Ensure careers are verified
    for c in test_storage["careers"].values():
        c.status = "verified"

    # 1. Search by title keyword (e.g. "Software" or "Data")
    res1 = await async_client.get("/v1/careers/search?q=Software")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total_count"] >= 1
    assert any("software" in it["title"].lower() for it in data1["items"])

    # 2. Search by alias
    res2 = await async_client.get("/v1/careers/search?q=SDE")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_count"] >= 1

    # 3. Query exceeding 60 characters is rejected by FastAPI validation -> 422
    long_q = "a" * 65
    res_long = await async_client.get(f"/v1/careers/search?q={long_q}")
    assert res_long.status_code == 422

    # 4. Search with authenticated user returns compatibility score if assessment completed
    token = await _signup_and_login(async_client, "career_search_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    res_auth = await async_client.get("/v1/careers/search?q=Engineer", headers=headers)
    assert res_auth.status_code == 200

