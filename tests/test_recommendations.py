import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from httpx import AsyncClient

from app.models.career import Certificate, Course
from app.models.roadmap import TemplateItem
from app.models.skill import Skill
from app.services.recommendation_engine import (
    filter_recommendation_candidates,
    is_item_active_and_verified,
    rank_recommendations,
)


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
async def test_engine_staleness_and_expiry():
    now = datetime.now(timezone.utc)

    # 1. Stale item (> 90 days since verification)
    stale_item = {
        "id": uuid4(),
        "status": "verified",
        "last_verified_at": now - timedelta(days=95),
        "expires_at": None,
        "application_deadline": None,
    }
    assert is_item_active_and_verified(stale_item, now=now, allow_drafts=False) is False

    # 2. Fresh verified item (< 90 days)
    fresh_item = {
        "id": uuid4(),
        "status": "verified",
        "last_verified_at": now - timedelta(days=20),
        "expires_at": None,
        "application_deadline": None,
    }
    assert is_item_active_and_verified(fresh_item, now=now, allow_drafts=False) is True

    # 3. Expired item (past expires_at)
    expired_item = {
        "id": uuid4(),
        "status": "verified",
        "last_verified_at": now - timedelta(days=5),
        "expires_at": now - timedelta(days=1),
        "application_deadline": None,
    }
    assert is_item_active_and_verified(expired_item, now=now, allow_drafts=False) is False

    # 4. Past application deadline
    past_deadline_item = {
        "id": uuid4(),
        "status": "verified",
        "last_verified_at": now - timedelta(days=5),
        "expires_at": None,
        "application_deadline": now - timedelta(hours=2),
    }
    assert is_item_active_and_verified(past_deadline_item, now=now, allow_drafts=False) is False

    # 5. Draft item in prod vs dev
    draft_item = {
        "id": uuid4(),
        "status": "draft",
        "last_verified_at": None,
        "expires_at": None,
        "application_deadline": None,
    }
    assert is_item_active_and_verified(draft_item, now=now, allow_drafts=False) is False
    assert is_item_active_and_verified(draft_item, now=now, allow_drafts=True) is True


@pytest.mark.asyncio
async def test_engine_filtering_budget_location_and_actions():
    now = datetime.now(timezone.utc)
    item_id1 = uuid4()
    item_id2 = uuid4()
    item_id3 = uuid4()

    candidates = [
        {
            "id": item_id1,
            "title": "Affordable Online Course",
            "item_type": "course",
            "cost_inr": 10000,
            "mode": "online",
            "location": None,
            "duration": "4 weeks",
            "status": "verified",
            "last_verified_at": now,
            "career_ids": [],
        },
        {
            "id": item_id2,
            "title": "Expensive Offline Academy",
            "item_type": "course",
            "cost_inr": 150000,
            "mode": "offline",
            "location": {"city": "Mumbai", "state": "Maharashtra"},
            "duration": "6 months",
            "status": "verified",
            "last_verified_at": now,
            "career_ids": [],
        },
        {
            "id": item_id3,
            "title": "Bangalore Internship",
            "item_type": "internship",
            "cost_inr": 0,
            "mode": "offline",
            "location": {"city": "Bangalore", "state": "Karnataka"},
            "locations": ["Bangalore"],
            "duration": "3 months",
            "status": "verified",
            "last_verified_at": now,
            "career_ids": [],
        },
    ]

    # Filter with low budget (<= 50,000 INR)
    filtered_low_budget = filter_recommendation_candidates(
        candidates,
        now=now,
        budget_level="low",
        allow_drafts=False,
    )
    ids_low = [c["id"] for c in filtered_low_budget]
    assert item_id1 in ids_low
    assert item_id3 in ids_low
    assert item_id2 not in ids_low  # 150k INR excluded from low budget

    # Filter with location "Bangalore"
    filtered_bangalore = filter_recommendation_candidates(
        candidates,
        now=now,
        user_location="Bangalore",
        allow_drafts=False,
    )
    ids_bgl = [c["id"] for c in filtered_bangalore]
    assert item_id1 in ids_bgl  # online matches all
    assert item_id3 in ids_bgl  # matches Bangalore
    assert item_id2 not in ids_bgl  # Mumbai excluded

    # Filter with user action: item_id1 is dismissed, item_id3 is done
    user_actions = {
        ("course", str(item_id1)): "dismissed",
        ("internship", str(item_id3)): "done",
    }
    filtered_actions = filter_recommendation_candidates(
        candidates,
        now=now,
        user_actions=user_actions,
        include_dismissed=False,
        allow_drafts=False,
    )
    # Both dismissed and done should be excluded
    ids_act = [c["id"] for c in filtered_actions]
    assert item_id1 not in ids_act
    assert item_id3 not in ids_act
    assert item_id2 in ids_act

    # Include dismissed flag
    filtered_with_dismissed = filter_recommendation_candidates(
        candidates,
        now=now,
        user_actions=user_actions,
        include_dismissed=True,
        allow_drafts=False,
    )
    ids_with_dis = [c["id"] for c in filtered_with_dismissed]
    assert item_id1 in ids_with_dis
    assert item_id3 not in ids_with_dis  # done still excluded


@pytest.mark.asyncio
async def test_engine_ranking_and_tiebreaking():
    target_career_id = uuid4()
    item_a_id = uuid4()
    item_b_id = uuid4()
    item_c_id = uuid4()

    candidates = [
        {
            "id": item_a_id,
            "title": "Zebra Advanced Systems",
            "item_type": "course",
            "cost_inr": 20000,
            "mode": "online",
            "career_ids": [target_career_id],
            "skills": [{"slug": "python", "name": "Python"}],
        },
        {
            "id": item_b_id,
            "title": "Alpha Cloud Fundamentals",
            "item_type": "certificate",
            "cost_inr": 20000,
            "mode": "online",
            "career_ids": [target_career_id],
            "skills": [],
        },
        {
            "id": item_c_id,
            "title": "Unrelated Art History",
            "item_type": "course",
            "cost_inr": 50000,
            "mode": "offline",
            "career_ids": [],
            "skills": [],
        },
    ]

    ranked = rank_recommendations(
        candidates,
        target_career_id=str(target_career_id),
        user_skill_levels={"python": 1.0},
        user_budget_level="medium",
        user_location=None,
    )

    # item_a addresses tested weak skill "python" (level 1.0 < 2.5) -> bonus score
    assert ranked[0]["id"] == item_a_id
    assert ranked[0]["match_score"] > ranked[1]["match_score"]
    # item_c has lowest score
    assert ranked[-1]["id"] == item_c_id

    # Test deterministic tie-breaking when scores are equal:
    item_b2 = dict(candidates[1])
    item_b2["id"] = uuid4()
    item_b2["title"] = "Beta Systems"
    tied_ranked = rank_recommendations(
        [candidates[1], item_b2],
        target_career_id=str(target_career_id),
    )
    # "Alpha Cloud Fundamentals" comes before "Beta Systems" alphabetically
    assert tied_ranked[0]["title"] == "Alpha Cloud Fundamentals"
    assert tied_ranked[1]["title"] == "Beta Systems"


@pytest.mark.asyncio
async def test_get_recommendations_auth_and_personalisation(async_client, test_storage):
    # 1. Unauthenticated request -> 401
    resp = await async_client.get("/v1/recommendations")
    assert resp.status_code == 401

    # 2. Register & login fresh user
    token = await _signup_and_login(async_client, "rec_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed verified course and template item in storage
    now = datetime.now(timezone.utc)
    career = next(iter(test_storage["careers"].values()))

    course_id = uuid4()
    course = Course(
        id=course_id,
        code="CS_REC_101",
        title="Verified CS Course",
        degree_level="bachelor",
        duration="3 months",
        cost_inr=15000,
        mode="online",
        source_url="https://example.com/course",
        status="verified",
        last_verified_at=now - timedelta(days=10),
        created_at=now,
    )
    course.careers = [career]
    test_storage["courses"][course_id] = course

    res_id = uuid4()
    res = TemplateItem(
        id=res_id,
        template_id=uuid4(),
        item_code="RES_FREE_01",
        type="video",
        title="Free Verified Tutorial",
        source_url="https://example.com/video",
        estimated_minutes=45,
        difficulty=1,
        topic="Programming",
        status="verified",
        last_verified_at=now - timedelta(days=5),
        created_at=now,
    )
    test_storage["template_items"][res_id] = res

    # 3. User with no profile -> personalised: False
    resp = await async_client.get("/v1/recommendations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["personalised"] is False
    assert len(data["items"]) >= 2
    # Verify free resource has is_free == True
    free_item = next(it for it in data["items"] if it["id"] == str(res_id))
    assert free_item["is_free"] is True
    assert free_item["cost_inr"] == 0

    # 4. Create student profile for user -> personalised: True
    profile_resp = await async_client.put(
        "/v1/profile",
        json={
            "name": "Rec Student",
            "budget_level": "medium",
            "hours_available_per_week": 20,
            "subjects_of_interest": ["Computer Science"],
            "skills": [{"name": "Python", "level": "intermediate"}],
        },
        headers=headers,
    )
    assert profile_resp.status_code == 200

    resp_pers = await async_client.get(f"/v1/recommendations?career_id={career.id}", headers=headers)
    assert resp_pers.status_code == 200
    pers_data = resp_pers.json()
    assert pers_data["personalised"] is True
    # The verified career course should rank prominently
    first_item = pers_data["items"][0]
    assert "why_it_fits" in first_item
    assert len(first_item["why_it_fits"]) > 0


@pytest.mark.asyncio
async def test_recommendation_action_lifecycle_and_evidence(async_client, test_storage):
    token = await _signup_and_login(async_client, "rec_action_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc)
    course_id = uuid4()
    course = Course(
        id=course_id,
        code="CS_ACT_101",
        title="Action Test Course",
        degree_level="bachelor",
        duration="4 months",
        cost_inr=5000,
        mode="online",
        source_url="https://example.com/act_course",
        status="verified",
        last_verified_at=now,
        created_at=now,
    )
    test_storage["courses"][course_id] = course

    # 1. Save action
    save_resp = await async_client.post(
        f"/v1/recommendations/course/{course_id}/action",
        json={"state": "saved"},
        headers=headers,
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["state"] == "saved"

    # 2. Dismiss action
    dismiss_resp = await async_client.post(
        f"/v1/recommendations/course/{course_id}/action",
        json={"state": "dismissed"},
        headers=headers,
    )
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["state"] == "dismissed"

    # In GET /v1/recommendations, the dismissed course is excluded
    list_resp = await async_client.get("/v1/recommendations", headers=headers)
    assert list_resp.status_code == 200
    item_ids = [it["id"] for it in list_resp.json()["items"]]
    assert str(course_id) not in item_ids

    # 3. Restore action via state "none"
    restore_resp = await async_client.post(
        f"/v1/recommendations/course/{course_id}/action",
        json={"state": "none"},
        headers=headers,
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["state"] == "none"

    # Course reappears in feed
    list_resp2 = await async_client.get("/v1/recommendations", headers=headers)
    item_ids2 = [it["id"] for it in list_resp2.json()["items"]]
    assert str(course_id) in item_ids2

    # 4. Mark "done" -> creates skill evidence
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        slug="action-test-skill",
        name="Action Test Skill",
        aliases=[],
        created_at=now,
    )
    test_storage["skills"][skill_id] = skill

    course.title = "Action Test Skill"

    done_resp = await async_client.post(
        f"/v1/recommendations/course/{course_id}/action",
        json={"state": "done"},
        headers=headers,
    )
    assert done_resp.status_code == 200
    assert done_resp.json()["state"] == "done"

    # Done items are excluded from recommendations feed
    list_resp3 = await async_client.get("/v1/recommendations", headers=headers)
    item_ids3 = [it["id"] for it in list_resp3.json()["items"]]
    assert str(course_id) not in item_ids3

    # Verify skill evidence was recorded
    evidences = list(test_storage["skill_evidence"].values())
    rec_ev = next((e for e in evidences if e.source_id == course_id), None)
    assert rec_ev is not None
    assert rec_ev.source_type == "project"
    assert rec_ev.level_signal == "intermediate"

    # Idempotent re-send of done
    done_resp_repeat = await async_client.post(
        f"/v1/recommendations/course/{course_id}/action",
        json={"state": "done"},
        headers=headers,
    )
    assert done_resp_repeat.status_code == 200
    # No duplicate evidence created
    matching_ev = [e for e in test_storage["skill_evidence"].values() if e.source_id == course_id]
    assert len(matching_ev) == 1


@pytest.mark.asyncio
async def test_recommendation_action_validation_and_errors(async_client, test_storage):
    token = await _signup_and_login(async_client, "rec_err_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Invalid item_type -> 422
    inv_type_resp = await async_client.post(
        f"/v1/recommendations/unsupported_type/{uuid4()}/action",
        json={"state": "saved"},
        headers=headers,
    )
    assert inv_type_resp.status_code == 422

    # 2. Unknown item_id -> 404
    non_existent_id = uuid4()
    not_found_resp = await async_client.post(
        f"/v1/recommendations/course/{non_existent_id}/action",
        json={"state": "saved"},
        headers=headers,
    )
    assert not_found_resp.status_code == 404

    # 3. Unverified draft item -> 404
    now = datetime.now(timezone.utc)
    draft_id = uuid4()
    draft_cert = Certificate(
        id=draft_id,
        code="CERT_DRAFT",
        name="Draft Cert",
        issuing_organization="Org",
        source_url="https://example.com/draft",
        status="draft",
        created_at=now,
    )
    test_storage["certificates"][draft_id] = draft_cert

    draft_action_resp = await async_client.post(
        f"/v1/recommendations/certificate/{draft_id}/action",
        json={"state": "saved"},
        headers=headers,
    )
    assert draft_action_resp.status_code == 404

    # 4. Extra fields forbidden (extra='forbid') -> 422
    extra_field_resp = await async_client.post(
        f"/v1/recommendations/course/{non_existent_id}/action",
        json={"state": "saved", "unknown_field": "disallowed"},
        headers=headers,
    )
    assert extra_field_resp.status_code == 422


@pytest.mark.asyncio
async def test_recommendation_action_rate_limiting(async_client, test_storage):
    token = await _signup_and_login(async_client, "rec_rate_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc)
    course_id = uuid4()
    course = Course(
        id=course_id,
        code="CS_RATE_101",
        title="Rate Test Course",
        degree_level="bachelor",
        duration="4 months",
        cost_inr=5000,
        mode="online",
        source_url="https://example.com/rate_course",
        status="verified",
        last_verified_at=now,
        created_at=now,
    )
    test_storage["courses"][course_id] = course

    # Send 30 requests (allowed limit)
    for _ in range(30):
        resp = await async_client.post(
            f"/v1/recommendations/course/{course_id}/action",
            json={"state": "saved"},
            headers=headers,
        )
        assert resp.status_code == 200

    # 31st request triggers rate limit -> 429
    over_resp = await async_client.post(
        f"/v1/recommendations/course/{course_id}/action",
        json={"state": "saved"},
        headers=headers,
    )
    assert over_resp.status_code == 429
    assert "rate limit" in over_resp.text.lower()
