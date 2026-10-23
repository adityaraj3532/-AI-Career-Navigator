"""Integration and API tests for /v1/progress endpoints."""
from datetime import date
from uuid import uuid4
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.profile import StudentProfile
from app.models.user import User
from app.services.progress_engine import get_week_monday


@pytest.mark.asyncio
async def test_progress_summary_returns_404_when_no_profile(async_client: AsyncClient, test_storage):
    """GET /v1/progress/summary returns 404 if student profile does not exist."""
    user = User(id=uuid4(), email="noprofile@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/v1/progress/summary", headers=headers)
    assert resp.status_code == 404
    assert "Student profile not found" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_progress_summary_get_never_writes(async_client: AsyncClient, test_storage):
    """GET /v1/progress/summary is pure read and creates no database records."""
    user = User(id=uuid4(), email="reader@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    profile = StudentProfile(id=uuid4(), user_id=user.id, name="Reader", timezone="Asia/Kolkata")
    test_storage["student_profiles"][profile.id] = profile

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/v1/progress/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["timezone"] == "Asia/Kolkata"
    assert data["current_streak"] == 0
    assert data["longest_streak"] == 0
    assert data["milestones"] == []
    assert data["weekly_goals"] == []


@pytest.mark.asyncio
async def test_weekly_goal_past_week_rejected(async_client: AsyncClient, test_storage):
    """PUT /v1/progress/weekly-goals rejects edits to past weeks."""
    user = User(id=uuid4(), email="goaluser@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    profile = StudentProfile(id=uuid4(), user_id=user.id, name="Goal User", timezone="Asia/Kolkata")
    test_storage["student_profiles"][profile.id] = profile

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Two weeks in the past Monday
    past_monday = date(2020, 1, 6)
    payload = {
        "week_start": past_monday.isoformat(),
        "goal_type": "roadmap_items",
        "target": 5,
    }

    resp = await async_client.put("/v1/progress/weekly-goals", json=payload, headers=headers)
    assert resp.status_code == 400
    assert "Cannot edit past week goals" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_weekly_goal_future_limit_rejected(async_client: AsyncClient, test_storage):
    """PUT /v1/progress/weekly-goals rejects edits beyond next week."""
    user = User(id=uuid4(), email="futureuser@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    profile = StudentProfile(id=uuid4(), user_id=user.id, name="Future User", timezone="Asia/Kolkata")
    test_storage["student_profiles"][profile.id] = profile

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    far_future_monday = date(2030, 1, 7)
    payload = {
        "week_start": far_future_monday.isoformat(),
        "goal_type": "roadmap_items",
        "target": 5,
    }

    resp = await async_client.put("/v1/progress/weekly-goals", json=payload, headers=headers)
    assert resp.status_code == 400
    assert "Cannot edit goals more than one week ahead" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_weekly_goal_extra_field_rejected(async_client: AsyncClient, test_storage):
    """PUT /v1/progress/weekly-goals forbids extra fields."""
    user = User(id=uuid4(), email="extrafield@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    profile = StudentProfile(id=uuid4(), user_id=user.id, name="Extra User", timezone="Asia/Kolkata")
    test_storage["student_profiles"][profile.id] = profile

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    current_monday = get_week_monday(today)

    payload = {
        "week_start": current_monday.isoformat(),
        "goal_type": "roadmap_items",
        "target": 5,
        "unauthorized_field": "injected",
    }

    resp = await async_client.put("/v1/progress/weekly-goals", json=payload, headers=headers)
    assert resp.status_code == 422
