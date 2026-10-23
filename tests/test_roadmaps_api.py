import pytest
from datetime import datetime, timezone
from uuid import uuid4
from httpx import AsyncClient

from app.models.roadmap import (
    RoadmapTemplate,
    TemplateItem,
    TemplatePhase,
)
from app.models.skill import Skill


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


@pytest.fixture(autouse=True)
def setup_verified_template(test_storage):
    now = datetime.now(timezone.utc)
    career = next(iter(test_storage["careers"].values()))
    career.status = "verified"

    # Seed skill
    sk_id = uuid4()
    sk = Skill(
        id=sk_id,
        slug="python-dsa",
        name="Python DSA",
        aliases=["dsa"],
        created_at=now,
    )
    test_storage["skills"][sk_id] = sk

    # Seed verified roadmap template
    tid = uuid4()
    tmpl = RoadmapTemplate(
        id=tid,
        career_id=career.id,
        version=1,
        title="Verified SDE Template",
        status="verified",
        last_verified_at=now,
        created_at=now,
    )
    test_storage["roadmap_templates"][tid] = tmpl

    pid = uuid4()
    phase = TemplatePhase(
        id=pid,
        template_id=tid,
        name="Phase 1: Foundations",
        phase_order=1,
        description="Core basics",
        created_at=now,
    )
    test_storage["template_phases"][pid] = phase

    i1_id = uuid4()
    it1 = TemplateItem(
        id=i1_id,
        template_id=tid,
        phase_id=pid,
        item_code="MOD1_P1",
        type="video",
        title="Intro to Data Structures",
        source_url="https://example.com/video1",
        estimated_minutes=60,
        difficulty=1,
        topic="Python DSA",
        skill_id=sk_id,
        prerequisites=[],
        optional=False,
        status="verified",
        sequence_order=1,
        created_at=now,
    )
    test_storage["template_items"][i1_id] = it1

    i2_id = uuid4()
    it2 = TemplateItem(
        id=i2_id,
        template_id=tid,
        phase_id=pid,
        item_code="MOD1_P2",
        type="project",
        title="Array Manipulation Project",
        source_url="https://example.com/proj1",
        estimated_minutes=120,
        difficulty=2,
        topic="Python DSA",
        skill_id=sk_id,
        prerequisites=["MOD1_P1"],
        optional=False,
        status="verified",
        sequence_order=2,
        created_at=now,
    )
    test_storage["template_items"][i2_id] = it2

    return {"career": career, "template": tmpl, "item1": it1, "item2": it2, "skill": sk}


@pytest.mark.asyncio
async def test_roadmap_creation_and_cloning(async_client: AsyncClient, test_storage, setup_verified_template):
    # 1. Unauthenticated request -> 401
    resp = await async_client.post("/v1/roadmaps", json={"career_id": str(uuid4())})
    assert resp.status_code == 401

    # 2. Authenticated user creates roadmap
    token = await _signup_and_login(async_client, "roadmap_creator@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career = setup_verified_template["career"]

    create_resp = await async_client.post(
        "/v1/roadmaps",
        json={"career_id": str(career.id), "hours_per_week": 10.0},
        headers=headers,
    )
    assert create_resp.status_code == 201
    data = create_resp.json()

    assert data["id"] is not None
    assert data["career_id"] == str(career.id)
    assert data["hours_per_week"] == 10.0
    assert data["completion_percentage"] == 0.0
    assert len(data["phases"]) == 1
    assert len(data["phases"][0]["items"]) == 2

    # Verify independent copy (cloning): roadmap item IDs must not match template item IDs
    item_ids = [it["id"] for it in data["phases"][0]["items"]]
    assert str(setup_verified_template["item1"].id) not in item_ids
    assert str(setup_verified_template["item2"].id) not in item_ids

    # 3. Duplicate active roadmap rejected -> 400
    dup_resp = await async_client.post(
        "/v1/roadmaps",
        json={"career_id": str(career.id), "hours_per_week": 10.0},
        headers=headers,
    )
    assert dup_resp.status_code == 400
    assert "already have an active roadmap" in dup_resp.text.lower()


@pytest.mark.asyncio
async def test_roadmap_get_and_ownership(async_client: AsyncClient, test_storage, setup_verified_template):
    token_a = await _signup_and_login(async_client, "road_user_a@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    career = setup_verified_template["career"]

    # User A creates roadmap
    res_a = await async_client.post(
        "/v1/roadmaps",
        json={"career_id": str(career.id), "hours_per_week": 12.0},
        headers=headers_a,
    )
    roadmap_id = res_a.json()["id"]

    # User A can get roadmap
    get_res_a = await async_client.get(f"/v1/roadmaps/{roadmap_id}", headers=headers_a)
    assert get_res_a.status_code == 200
    assert get_res_a.json()["id"] == roadmap_id

    # User B cannot access User A's roadmap -> 404
    token_b = await _signup_and_login(async_client, "road_user_b@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    get_res_b = await async_client.get(f"/v1/roadmaps/{roadmap_id}", headers=headers_b)
    assert get_res_b.status_code == 404


@pytest.mark.asyncio
async def test_roadmap_item_status_transitions_and_evidence(async_client, test_storage, setup_verified_template):
    token = await _signup_and_login(async_client, "road_item_worker@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career = setup_verified_template["career"]

    res = await async_client.post(
        "/v1/roadmaps",
        json={"career_id": str(career.id), "hours_per_week": 15.0},
        headers=headers,
    )
    roadmap = res.json()
    item1 = roadmap["phases"][0]["items"][0]
    item1_id = item1["id"]

    # 1. Update status: todo -> in_progress
    patch1 = await async_client.patch(
        f"/v1/roadmaps/items/{item1_id}",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert patch1.status_code == 200
    assert patch1.json()["status"] == "in_progress"

    # 2. Update status: in_progress -> done (records completion and triggers skill evidence)
    patch2 = await async_client.patch(
        f"/v1/roadmaps/items/{item1_id}",
        json={"status": "done"},
        headers=headers,
    )
    assert patch2.status_code == 200
    assert patch2.json()["status"] == "done"
    assert patch2.json()["completed_at"] is not None

    # Check Skill Evidence was created in Skill Tracker
    ev_list = list(test_storage["skill_evidence"].values())
    rec_ev = next((e for e in ev_list if str(e.source_id) == item1_id), None)
    assert rec_ev is not None
    assert rec_ev.source_type == "roadmap"
    assert rec_ev.level_signal == "intermediate"

    # 3. Done is final: attempting to move back to todo without force_undo fails -> 400
    patch3 = await async_client.patch(
        f"/v1/roadmaps/items/{item1_id}",
        json={"status": "todo", "force_undo": False},
        headers=headers,
    )
    assert patch3.status_code == 400
    assert "done" in patch3.text.lower()

    # With force_undo=True, transition is allowed
    patch4 = await async_client.patch(
        f"/v1/roadmaps/items/{item1_id}",
        json={"status": "todo", "force_undo": True},
        headers=headers,
    )
    assert patch4.status_code == 200
    assert patch4.json()["status"] == "todo"


@pytest.mark.asyncio
async def test_roadmap_replan_and_rate_limiting(async_client, test_storage, setup_verified_template):
    token = await _signup_and_login(async_client, "road_replan_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    career = setup_verified_template["career"]

    res = await async_client.post(
        "/v1/roadmaps",
        json={"career_id": str(career.id), "hours_per_week": 8.0},
        headers=headers,
    )
    roadmap_id = res.json()["id"]

    # 1. First replan succeeds
    replan1 = await async_client.post(
        f"/v1/roadmaps/{roadmap_id}/replan",
        json={"hours_per_week": 10.0},
        headers=headers,
    )
    assert replan1.status_code == 200
    data1 = replan1.json()
    assert data1["roadmap_id"] == roadmap_id
    assert "summary" in data1

    # Second and third replan succeed
    await async_client.post(f"/v1/roadmaps/{roadmap_id}/replan", json={}, headers=headers)
    await async_client.post(f"/v1/roadmaps/{roadmap_id}/replan", json={}, headers=headers)

    # 4th replan within 7 days triggers rate limit -> 429
    replan4 = await async_client.post(
        f"/v1/roadmaps/{roadmap_id}/replan",
        json={},
        headers=headers,
    )
    assert replan4.status_code == 429
    assert "replan limit" in replan4.text.lower()
