from datetime import datetime, timezone
from uuid import uuid4
import pytest
from httpx import AsyncClient

from app.models.skill import Skill, SkillEvidence, UserSkill


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
async def test_portfolio_unauthenticated(async_client: AsyncClient):
    resp = await async_client.get("/v1/portfolio")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_portfolio_creates_no_rows_and_returns_draft_suggestions(async_client: AsyncClient, test_storage):
    """GET /v1/portfolio must not write to the database and return is_persisted=False."""
    token = await _signup_and_login(async_client, "no_write_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    initial_row_count = len(test_storage.get("user_portfolios", {}))

    resp = await async_client.get("/v1/portfolio", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Invariant: GET creates no rows
    assert len(test_storage.get("user_portfolios", {})) == initial_row_count
    assert data["is_persisted"] is False
    assert data["is_public"] is False
    assert data["slug"].startswith("u-")
    assert data["visibility"] == {
        "about": False,
        "skills": False,
        "projects": False,
        "certificates": False,
        "competitions": False,
        "achievements": False,
    }
    assert data["headline"] is None
    assert data["about"] is None


@pytest.mark.asyncio
async def test_put_portfolio_creates_row_and_persists(async_client: AsyncClient, test_storage):
    """PUT /v1/portfolio creates the row in the database on first save."""
    token = await _signup_and_login(async_client, "persisted_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "slug": "jane-developer",
        "is_public": True,
        "headline": "Full-Stack Engineer & Systems Specialist",
        "about": "Passionate developer building high-throughput distributed systems.",
        "visibility": {
            "about": True,
            "skills": True,
            "projects": True,
            "certificates": True,
            "competitions": False,
            "achievements": False,
        },
        "custom_projects": [
            {
                "title": "Cloud File Storage",
                "description": "Built distributed S3-compatible microservice with FastAPI and asyncio.",
                "skills": ["Python", "FastAPI", "Docker"],
                "link": "https://github.com/example/storage",
                "completed_date": "2026-05-15",
                "provenance": "self_reported",
            }
        ],
        "custom_certificates": [
            {
                "title": "AWS Certified Developer",
                "issuer": "Amazon Web Services",
                "credential_url": "https://aws.amazon.com/verify/123",
                "issue_date": "2026-06-01",
                "provenance": "self_reported",
            }
        ],
        "competitions": [
            {
                "title": "National Hackathon 2026",
                "award_or_rank": "1st Place Winner",
                "description": "Architected low-latency microservices pipeline.",
                "year": 2026,
            }
        ],
        "achievements": [
            {
                "title": "Dean's Honor List",
                "description": "Top 1% academic standing in Computer Science.",
                "date": "2026-04",
            }
        ],
    }

    put_res = await async_client.put("/v1/portfolio", json=payload, headers=headers)
    assert put_res.status_code == 200
    data = put_res.json()

    assert data["is_persisted"] is True
    assert data["slug"] == "jane-developer"
    assert data["is_public"] is True
    assert data["headline"] == "Full-Stack Engineer & Systems Specialist"
    assert len(data["projects"]) >= 1
    assert data["projects"][0]["title"] == "Cloud File Storage"
    assert data["visibility"]["about"] is True

    # Check persistence in test storage
    assert len(test_storage["user_portfolios"]) >= 1


@pytest.mark.asyncio
async def test_slug_rules_and_reserved_words(async_client: AsyncClient):
    """Verify slug validation: regex, bounds, and reserved words list."""
    token = await _signup_and_login(async_client, "slug_rules@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Too short (< 3 chars)
    r_short = await async_client.put("/v1/portfolio", json={"slug": "ab"}, headers=headers)
    assert r_short.status_code == 422

    # Invalid characters / regex
    r_invalid = await async_client.put("/v1/portfolio", json={"slug": "invalid_slug!"}, headers=headers)
    assert r_invalid.status_code == 422

    # Consecutive or leading hyphens
    r_hyphen = await async_client.put("/v1/portfolio", json={"slug": "-bad-slug-"}, headers=headers)
    assert r_hyphen.status_code == 422

    # Reserved words
    for reserved in ["admin", "api", "auth", "login", "settings", "root"]:
        r_res = await async_client.put("/v1/portfolio", json={"slug": reserved}, headers=headers)
        assert r_res.status_code == 422
        assert "reserved system keyword" in r_res.text


@pytest.mark.asyncio
async def test_concurrent_slug_claim_conflict(async_client: AsyncClient):
    """Claiming an existing slug returns 409 Conflict."""
    token1 = await _signup_and_login(async_client, "user_one_slug@example.com")
    token2 = await _signup_and_login(async_client, "user_two_slug@example.com")

    # User 1 claims slug
    r1 = await async_client.put("/v1/portfolio", json={"slug": "unique-portfolio"}, headers={"Authorization": f"Bearer {token1}"})
    assert r1.status_code == 200

    # User 2 attempts to claim same slug
    r2 = await async_client.put("/v1/portfolio", json={"slug": "unique-portfolio"}, headers={"Authorization": f"Bearer {token2}"})
    assert r2.status_code == 409
    assert "already claimed" in r2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_extra_fields_and_bad_links_rejected(async_client: AsyncClient):
    """extra='forbid' and link scheme validation."""
    token = await _signup_and_login(async_client, "validation_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Extra field on root
    r_extra = await async_client.put("/v1/portfolio", json={"hacked_field": True}, headers=headers)
    assert r_extra.status_code == 422

    # Bad link scheme (not http/https)
    r_bad_link = await async_client.put(
        "/v1/portfolio",
        json={
            "custom_projects": [
                {
                    "title": "Bad Link Project",
                    "description": "Testing invalid links",
                    "link": "javascript:alert(1)",
                }
            ]
        },
        headers=headers,
    )
    assert r_bad_link.status_code == 422


@pytest.mark.asyncio
async def test_provenance_labels_for_skills_and_roadmap_items(async_client: AsyncClient, test_storage):
    """Verify provenance: test_assessed when test evidence exists; completed roadmap items labelled self_reported."""
    token = await _signup_and_login(async_client, "provenance_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user = next(u for u in test_storage["users"].values() if u.email == "provenance_user@example.com")
    now = datetime.now(timezone.utc)

    # 1. Add skill with test evidence
    sk1_id = uuid4()
    skill1 = Skill(id=sk1_id, slug="golang", name="Go", created_at=now)
    test_storage["skills"][sk1_id] = skill1

    us1_id = uuid4()
    us1 = UserSkill(id=us1_id, user_id=user.id, skill_id=sk1_id, current_level="intermediate", confidence="high", updated_at=now)
    us1.skill = skill1
    test_storage["user_skills"][us1_id] = us1

    ev_id = uuid4()
    ev = SkillEvidence(id=ev_id, user_id=user.id, skill_id=sk1_id, source_type="test", source_id=uuid4(), score=85, created_at=now)
    test_storage["skill_evidence"][ev_id] = ev

    # 2. Add skill without test evidence (declared only)
    sk2_id = uuid4()
    skill2 = Skill(id=sk2_id, slug="rust", name="Rust", created_at=now)
    test_storage["skills"][sk2_id] = skill2

    us2_id = uuid4()
    us2 = UserSkill(id=us2_id, user_id=user.id, skill_id=sk2_id, current_level="beginner", confidence="low", updated_at=now)
    us2.skill = skill2
    test_storage["user_skills"][us2_id] = us2

    resp = await async_client.get("/v1/portfolio", headers=headers)
    assert resp.status_code == 200
    skills_data = {s["slug"]: s for s in resp.json()["skills"]}

    assert skills_data["golang"]["provenance"] == "test_assessed"
    assert skills_data["rust"]["provenance"] == "self_reported"


@pytest.mark.asyncio
async def test_public_portfolio_allowlist_headers_and_visibility(async_client: AsyncClient):
    """Public page GET /v1/portfolio/p/{slug} allowlist, visibility toggles, and headers."""
    token = await _signup_and_login(async_client, "public_portfolio_owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Private by default -> returns 404
    await async_client.put(
        "/v1/portfolio",
        json={
            "slug": "public-dev-slug",
            "is_public": False,
            "headline": "Backend Engineer",
            "about": "Secret private about text",
            "visibility": {"about": True, "skills": True, "projects": True, "certificates": False, "competitions": False, "achievements": False},
        },
        headers=headers,
    )

    r_private = await async_client.get("/v1/portfolio/p/public-dev-slug")
    assert r_private.status_code == 404

    # 2. Toggle is_public to True
    await async_client.put(
        "/v1/portfolio",
        json={
            "is_public": True,
            "headline": "Backend Engineer",
            "about": "Publicly visible about text",
            "visibility": {"about": True, "skills": False, "projects": False, "certificates": False, "competitions": False, "achievements": False},
        },
        headers=headers,
    )

    r_pub = await async_client.get("/v1/portfolio/p/public-dev-slug")
    assert r_pub.status_code == 200
    assert r_pub.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert "no-cache" in r_pub.headers["Cache-Control"]

    pub_data = r_pub.json()
    assert pub_data["slug"] == "public-dev-slug"
    assert pub_data["about"] == "Publicly visible about text"

    # Invariant: Forbidden keys are NEVER present in public view
    forbidden_keys = ["email", "user_id", "hashed_password", "id", "user_portfolio_id"]
    for key in forbidden_keys:
        assert key not in pub_data

    # Hidden sections whose visibility is False are absent/None
    assert pub_data["skills"] is None
    assert pub_data["projects"] is None
    assert pub_data["certificates"] is None

    # Unknown slug returns 404
    r_unknown = await async_client.get("/v1/portfolio/p/nonexistent-random-slug-123")
    assert r_unknown.status_code == 404


@pytest.mark.asyncio
async def test_ai_text_assistant_generate_text(async_client: AsyncClient):
    """POST /v1/portfolio/generate-text strictly based on facts without hallucinating numbers."""
    token = await _signup_and_login(async_client, "ai_assistant_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid request
    res = await async_client.post(
        "/v1/portfolio/generate-text",
        json={
            "section": "about",
            "user_facts": [
                "Built asynchronous REST APIs with FastAPI",
                "Optimized database connection pools with SQLAlchemy",
                "Reduced cache query latency using Redis",
            ],
            "target_career": "Backend Engineer",
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["section"] == "about"
    assert data["is_suggestion"] is True
    assert len(data["generated_text"]) > 10
    assert data["word_count"] > 0

    # 2. Empty facts rejected
    res_empty = await async_client.post(
        "/v1/portfolio/generate-text",
        json={"section": "about", "user_facts": ["   "]},
        headers=headers,
    )
    assert res_empty.status_code == 422

    # 3. Fact longer than 200 chars rejected
    res_long = await async_client.post(
        "/v1/portfolio/generate-text",
        json={"section": "about", "user_facts": ["a" * 205]},
        headers=headers,
    )
    assert res_long.status_code == 422
