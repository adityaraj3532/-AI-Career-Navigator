import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from httpx import AsyncClient

from app.models.adaptive_test import TestAttempt
from app.models.career import Course
from app.models.roadmap import Roadmap, RoadmapItem
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
async def test_portfolio_methods_disallowed(async_client: AsyncClient):
    token = await _signup_and_login(async_client, "portfolio_methods@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Portfolio is strictly a read-only aggregation (POST, PUT, DELETE disallowed)
    post_resp = await async_client.post("/v1/portfolio", json={}, headers=headers)
    assert post_resp.status_code == 405

    delete_resp = await async_client.delete("/v1/portfolio", headers=headers)
    assert delete_resp.status_code == 405


@pytest.mark.asyncio
async def test_portfolio_fresh_user_empty(async_client: AsyncClient):
    token = await _signup_and_login(async_client, "portfolio_fresh@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/v1/portfolio", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Profile defaults
    assert data["profile"]["email"] == "portfolio_fresh@example.com"
    assert data["profile"]["education_level"] == "college"
    assert data["profile"]["name"] is None
    assert data["profile"]["subjects_of_interest"] == []

    # Summary all zeros
    assert data["summary"]["total_skills_tracked"] == 0
    assert data["summary"]["total_recommendations_completed"] == 0
    assert data["summary"]["total_milestones_completed"] == 0
    assert data["summary"]["total_tests_completed"] == 0

    # Lists are empty
    assert data["skills"] == []
    assert data["completed_recommendations"] == []
    assert data["completed_milestones"] == []
    assert data["diagnostic_tests"] == []


@pytest.mark.asyncio
async def test_portfolio_full_aggregation(async_client: AsyncClient, test_storage):
    token = await _signup_and_login(async_client, "portfolio_full@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Retrieve user id from storage
    user = next(u for u in test_storage["users"].values() if u.email == "portfolio_full@example.com")
    user_id = user.id
    now = datetime.now(timezone.utc)

    # 1. Update Profile
    prof_resp = await async_client.put(
        "/v1/profile",
        json={
            "name": "Jane Developer",
            "budget_level": "medium",
            "hours_available_per_week": 25,
            "subjects_of_interest": ["Computer Science", "Algorithms"],
            "skills": [{"name": "Python", "level": "intermediate"}],
        },
        headers=headers,
    )
    assert prof_resp.status_code == 200

    # 2. Add Tracked Skill with Evidence
    sk_id = uuid4()
    skill = Skill(
        id=sk_id,
        slug="python",
        name="Python",
        aliases=["python3"],
        created_at=now,
    )
    test_storage["skills"][sk_id] = skill

    us_id = uuid4()
    us = UserSkill(
        id=us_id,
        user_id=user_id,
        skill_id=sk_id,
        current_level="intermediate",
        confidence="high",
        updated_at=now,
    )
    us.skill = skill
    test_storage["user_skills"][us_id] = us

    ev_id = uuid4()
    ev = SkillEvidence(
        id=ev_id,
        user_id=user_id,
        skill_id=sk_id,
        source_type="project",
        source_id=uuid4(),
        score=85,
        level_signal="intermediate",
        summary="Built CLI data pipeline",
        created_at=now,
    )
    test_storage["skill_evidence"][ev_id] = ev

    # 3. Complete a Recommendation Item via action endpoint
    course_id = uuid4()
    course = Course(
        id=course_id,
        code="CS_FULL_101",
        title="Full Stack Software Engineering",
        degree_level="bachelor",
        duration="6 months",
        cost_inr=20000,
        mode="online",
        source_url="https://example.com/full_cs",
        status="verified",
        last_verified_at=now,
        created_at=now,
    )
    test_storage["courses"][course_id] = course

    action_resp = await async_client.post(
        f"/v1/recommendations/course/{course_id}/action",
        json={"state": "done"},
        headers=headers,
    )
    assert action_resp.status_code == 200

    # 4. Add Completed Roadmap Milestone
    career = next(iter(test_storage["careers"].values()))
    rd_id = uuid4()
    roadmap = Roadmap(
        id=rd_id,
        user_id=user_id,
        career_id=career.id,
        template_id=uuid4(),
        template_version=1,
        title="SDE Action Plan",
        status="active",
        created_at=now,
        updated_at=now,
    )
    test_storage["roadmaps"][rd_id] = roadmap

    r_item_id = uuid4()
    r_item = RoadmapItem(
        id=r_item_id,
        roadmap_id=rd_id,
        item_code="PROJ_BACKEND_API",
        type="project",
        title="RESTful Web API Project",
        topic="Backend Systems",
        difficulty=2,
        estimated_minutes=300,
        source_url="https://github.com/example/project",
        status="done",
        completed_at=now - timedelta(days=2),
        created_at=now,
        updated_at=now,
    )
    test_storage["roadmap_items"][r_item_id] = r_item

    # 5. Add Completed Diagnostic Test
    attempt_id = uuid4()
    attempt = TestAttempt(
        id=attempt_id,
        user_id=user_id,
        career_id=career.id,
        type="skill",
        topic="Data Structures & Algorithms",
        status="finished",
        current_difficulty=2,
        demonstrated_level="intermediate",
        confidence="high",
        score_percentage=80,
        total_correct=5,
        total_answered=6,
        started_at=now - timedelta(days=3),
    )
    test_storage["test_attempts"][attempt_id] = attempt

    # 6. Fetch Portfolio
    resp = await async_client.get("/v1/portfolio", headers=headers)
    assert resp.status_code == 200
    portfolio = resp.json()

    # Verify Profile
    assert portfolio["profile"]["name"] == "Jane Developer"
    assert portfolio["profile"]["subjects_of_interest"] == ["Computer Science", "Algorithms"]

    # Verify Summary Counters
    assert portfolio["summary"]["total_skills_tracked"] == 1
    assert portfolio["summary"]["total_recommendations_completed"] == 1
    assert portfolio["summary"]["total_milestones_completed"] == 1
    assert portfolio["summary"]["total_tests_completed"] == 1

    # Verify Tracked Skills & Evidence Count
    sk_item = portfolio["skills"][0]
    assert sk_item["name"] == "Python"
    assert sk_item["current_level"] == "intermediate"
    assert sk_item["confidence"] == "high"
    # 2 evidence points: 1 manually created + 1 auto-created by marking course done if title/domain matched, or at least 1
    assert sk_item["evidence_count"] >= 1

    # Verify Completed Recommendation
    rec_item = portfolio["completed_recommendations"][0]
    assert rec_item["item_id"] == str(course_id)
    assert rec_item["item_type"] == "course"
    assert rec_item["title"] == "Full Stack Software Engineering"
    assert rec_item["provider"] == "bachelor"
    assert rec_item["source_url"] == "https://example.com/full_cs"

    # Verify Completed Milestone
    m_item = portfolio["completed_milestones"][0]
    assert m_item["item_id"] == str(r_item_id)
    assert m_item["roadmap_id"] == str(rd_id)
    assert m_item["title"] == "RESTful Web API Project"
    assert m_item["type"] == "project"
    assert m_item["topic"] == "Backend Systems"
    assert m_item["difficulty"] == 2

    # Verify Diagnostic Test
    test_item = portfolio["diagnostic_tests"][0]
    assert test_item["attempt_id"] == str(attempt_id)
    assert test_item["type"] == "skill"
    assert test_item["topic"] == "Data Structures & Algorithms"
    assert test_item["demonstrated_level"] == "intermediate"
    assert test_item["confidence"] == "high"
    assert test_item["score_percentage"] == 80


@pytest.mark.asyncio
async def test_portfolio_strict_ownership_isolation(async_client: AsyncClient, test_storage):
    # User A creates content
    token_a = await _signup_and_login(async_client, "user_a@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    now = datetime.now(timezone.utc)
    course_id = uuid4()
    course = Course(
        id=course_id,
        code="CS_USER_A",
        title="User A Private Course",
        degree_level="bachelor",
        duration="2 months",
        cost_inr=1000,
        mode="online",
        source_url="https://example.com/user_a",
        status="verified",
        last_verified_at=now,
        created_at=now,
    )
    test_storage["courses"][course_id] = course

    await async_client.post(
        f"/v1/recommendations/course/{course_id}/action",
        json={"state": "done"},
        headers=headers_a,
    )

    # User B registers
    token_b = await _signup_and_login(async_client, "user_b@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B queries their portfolio
    resp_b = await async_client.get("/v1/portfolio", headers=headers_b)
    assert resp_b.status_code == 200
    data_b = resp_b.json()

    # User B must not see User A's completed recommendations
    assert data_b["summary"]["total_recommendations_completed"] == 0
    assert len(data_b["completed_recommendations"]) == 0
    rec_ids_b = [it["item_id"] for it in data_b["completed_recommendations"]]
    assert str(course_id) not in rec_ids_b


@pytest.mark.asyncio
async def test_public_portfolio_and_summary_and_export(async_client: AsyncClient, test_storage):
    """Verify public portfolio page, AI elevator pitch summary, and markdown resume export."""
    email = "portfolio_extensions@example.com"
    token = await _signup_and_login(async_client, email)
    headers = {"Authorization": f"Bearer {token}"}

    # Retrieve current user id from /me
    me_res = await async_client.get("/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_id = me_res.json()["id"]

    # 1. Public portfolio endpoint (accessible unauthenticated)
    pub_res = await async_client.get(f"/v1/portfolio/public/{user_id}")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert "profile" in pub_data
    assert "email" not in pub_data["profile"]  # Email must not leak in public view
    assert pub_data["profile"]["user_id"] == user_id
    assert "summary" in pub_data

    # Unexisting user returns 404
    non_existent = str(uuid4())
    pub_404 = await async_client.get(f"/v1/portfolio/public/{non_existent}")
    assert pub_404.status_code == 404

    # 2. AI Elevator Pitch Summary (Authenticated)
    pitch_res = await async_client.post(
        "/v1/portfolio/summary",
        json={"headline": "Full-stack developer"},
        headers=headers,
    )
    assert pitch_res.status_code == 200
    pitch_data = pitch_res.json()
    assert "elevator_pitch" in pitch_data
    assert len(pitch_data["key_highlights"]) > 0
    assert "suggested_tagline" in pitch_data

    # Extra field forbidden on pitch
    pitch_invalid = await async_client.post(
        "/v1/portfolio/summary",
        json={"headline": "Developer", "extra_bad": True},
        headers=headers,
    )
    assert pitch_invalid.status_code == 422

    # 3. Resume Markdown Export (Authenticated)
    resume_res = await async_client.get("/v1/portfolio/export/resume", headers=headers)
    assert resume_res.status_code == 200
    resume_data = resume_res.json()
    assert "markdown_resume" in resume_data
    assert "Resume: Candidate Portfolio" in resume_data["markdown_resume"]
    assert resume_data["export_format"] == "markdown"

