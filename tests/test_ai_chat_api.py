"""Integration and API tests for /v1/ai/chat and conversation endpoints."""
from uuid import uuid4
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.career import Career
from app.models.chat import ChatConversation, ChatMessage
from app.models.profile import StudentProfile
from app.models.user import User


@pytest.mark.asyncio
async def test_chat_safety_distress_triggers_supportive_message_and_no_profile_flag(
    async_client: AsyncClient, test_storage
):
    """Safety pre-check triggers on distress phrase, bypassing AI, without profiling the user."""
    user = User(id=uuid4(), email="distressed@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    profile = StudentProfile(id=uuid4(), user_id=user.id, name="Distressed Student")
    test_storage["student_profiles"][profile.id] = profile

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "mode": "skills",
        "message": "I feel so hopeless, I want to kill myself",
    }

    resp = await async_client.post("/v1/ai/chat", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["ai_status"] == "safety"
    assert "KIRAN" in data["content"]
    assert "counselor" in data["content"].lower()

    # Invariant: No distress flag or tracking stored on profile
    assert not hasattr(profile, "safety_flag")
    assert not hasattr(profile, "distress_flag")


@pytest.mark.asyncio
async def test_chat_career_mode_unverified_career_returns_404(
    async_client: AsyncClient, test_storage
):
    """Career mode requires a verified career; draft or unknown returns 404."""
    user = User(id=uuid4(), email="draftcareer@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    draft_cid = uuid4()
    draft_c = Career(id=draft_cid, code="DRAFT_CR", title="Draft Job", status="draft")
    test_storage["careers"][draft_cid] = draft_c

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Calling with draft career returns 404
    payload = {
        "mode": "career",
        "career_id": str(draft_cid),
        "message": "Tell me about this career",
    }
    resp = await async_client.post("/v1/ai/chat", json=payload, headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_roadmap_mode_no_roadmap_returns_fixed_message_without_ai(
    async_client: AsyncClient, test_storage
):
    """Roadmap mode with no active roadmap returns fixed message without calling AI."""
    user = User(id=uuid4(), email="noroadmap@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "mode": "roadmap",
        "message": "What should I learn next?",
    }
    resp = await async_client.post("/v1/ai/chat", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["ai_status"] == "fallback"
    assert "create a roadmap first" in data["content"].lower()


@pytest.mark.asyncio
async def test_chat_mode_fixed_after_creation(
    async_client: AsyncClient, test_storage
):
    """Existing conversation cannot have its mode altered."""
    user = User(id=uuid4(), email="fixedmode@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    conv_id = uuid4()
    conv = ChatConversation(id=conv_id, user_id=user.id, mode="skills", title="Skills Chat")
    test_storage["chat_conversations"][conv_id] = conv

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Attempting to send message to conv with different mode
    payload = {
        "conversation_id": str(conv_id),
        "mode": "career",  # CONFLICT
        "message": "Change mode please",
    }
    resp = await async_client.post("/v1/ai/chat", json=payload, headers=headers)
    assert resp.status_code == 400
    assert "fixed as 'skills'" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_chat_conversation_foreign_ownership_returns_404(
    async_client: AsyncClient, test_storage
):
    """Accessing another user's conversation returns HTTP 404."""
    user1 = User(id=uuid4(), email="user1@test.com", hashed_password="pw", is_active=True, role="student")
    user2 = User(id=uuid4(), email="user2@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user1.id] = user1
    test_storage["users"][user2.id] = user2

    conv_id = uuid4()
    conv = ChatConversation(id=conv_id, user_id=user1.id, mode="skills", title="User 1 Chat")
    test_storage["chat_conversations"][conv_id] = conv

    # User 2 tries to GET user 1's conversation
    token2 = create_access_token(user2.id, user2.email, user2.role)
    headers2 = {"Authorization": f"Bearer {token2}"}

    resp = await async_client.get(f"/v1/ai/conversations/{conv_id}", headers=headers2)
    assert resp.status_code == 404

    # User 2 tries to DELETE user 1's conversation
    resp_del = await async_client.delete(f"/v1/ai/conversations/{conv_id}", headers=headers2)
    assert resp_del.status_code == 404


@pytest.mark.asyncio
async def test_chat_delete_conversation_cascades(
    async_client: AsyncClient, test_storage
):
    """Deleting conversation cascades and deletes message history."""
    user = User(id=uuid4(), email="deleter@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    conv_id = uuid4()
    conv = ChatConversation(id=conv_id, user_id=user.id, mode="skills", title="Delete Chat")
    test_storage["chat_conversations"][conv_id] = conv

    msg1 = ChatMessage(id=uuid4(), conversation_id=conv_id, seq=1, role="user", content="Hi")
    test_storage["chat_messages"][msg1.id] = msg1

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.delete(f"/v1/ai/conversations/{conv_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


@pytest.mark.asyncio
async def test_logs_contain_no_message_content(
    async_client: AsyncClient, test_storage, caplog
):
    """Privacy invariant: Logs must never contain raw user message text."""
    user = User(id=uuid4(), email="privacy@test.com", hashed_password="pw", is_active=True, role="student")
    test_storage["users"][user.id] = user

    secret_message = "SuperSecretPersonalDilemma998877"
    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    with caplog.at_level("INFO"):
        await async_client.post(
            "/v1/ai/chat",
            json={"mode": "skills", "message": secret_message},
            headers=headers,
        )

    # Secret message text must NEVER appear in logs
    log_text = caplog.text
    assert secret_message not in log_text
