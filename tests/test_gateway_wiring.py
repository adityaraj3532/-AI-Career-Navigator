import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.core.config import get_settings
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.llm.provider import MockLLMProvider
from app.llm.telemetry import get_fallback_counts, reset_telemetry_counters
from app.models.career import Career
from app.models.interview import InterviewQuestion, InterviewSession, SessionQuestion
from app.models.profile import StudentProfile
from app.models.user import User


def test_no_module_outside_app_llm_imports_provider_sdk_or_calls_model():
    """Security Invariant: No module outside app/llm may import a provider SDK or call a model directly."""
    app_root = Path(__file__).resolve().parent.parent / "app"
    forbidden_modules = {
        "google.genai",
        "google.ai",
        "openai",
        "anthropic",
        "app.llm.provider.GeminiProvider",
        "app.llm.provider.MockLLMProvider",
    }

    violations = []

    for py_file in app_root.rglob("*.py"):
        # Allow files strictly within app/llm
        rel_path = py_file.relative_to(app_root)
        if rel_path.parts[0] == "llm":
            continue

        source_code = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source_code, filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        if alias.name == forbidden or alias.name.startswith(forbidden + "."):
                            violations.append((str(rel_path), f"import {alias.name}"))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for forbidden in forbidden_modules:
                    if mod == forbidden or mod.startswith(forbidden + "."):
                        violations.append((str(rel_path), f"from {mod} import ..."))

    assert not violations, f"Architectural Isolation Violation! Forbidden provider imports found:\n{violations}"


@pytest.mark.asyncio
async def test_ready_probe_fails_if_gateway_not_configured_in_non_test_env(async_client: AsyncClient, monkeypatch):
    """Resilience Invariant: /v1/ready fails (HTTP 503) if the LLM gateway is unconfigured in production."""
    settings = get_settings()

    # Emulate production environment without GEMINI_API_KEY
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    resp = await async_client.get("/v1/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "not_ready"
    assert data["dependencies"]["llm_gateway"] == "unhealthy"


@pytest.mark.asyncio
async def test_ai_feature_wiring_language_advisor(async_client: AsyncClient, test_storage):
    """Integration: POST /v1/tests/language-advisor executed via LLMGateway with MockLLMProvider."""
    user = User(id=uuid4(), email="lang_advisor@example.com", hashed_password="pw", role="student", is_active=True)
    test_storage["users"][user.id] = user
    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    gateway = get_llm_gateway()
    mock_provider: MockLLMProvider = gateway.provider
    mock_provider.queue_response(
        json.dumps({
            "why_it_fits": "AI-Generated: Python offers unparalleled ecosystem breadth for machine learning pipelines.",
            "next_steps": ["Install Jupyter", "Master Pandas dataframes", "Build first classification model"],
        })
    )

    req = {"primary_goal": "machine_learning", "prior_experience": "beginner", "target_role": "Data Scientist"}
    resp = await async_client.post("/v1/tests/language-advisor", json=req, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "AI-Generated" in data["why_it_fits"]
    assert data["recommended_language"] == "python"


@pytest.mark.asyncio
async def test_ai_feature_wiring_interview_evaluation_booleans_only(async_client: AsyncClient, test_storage):
    """Integration: POST /v1/interviews/{id}/answers evaluates key points via AI booleans only; code computes scores."""
    user = User(id=uuid4(), email="interview_candidate@example.com", hashed_password="pw", role="student", is_active=True)
    test_storage["users"][user.id] = user
    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    career = Career(
        id=uuid4(),
        code="SWE",
        title="Software Engineer",
        cluster="Engineering",
        overview="Builds software systems.",
        status="verified",
        salary_ranges={"entry_avg_inr": 1200000},
    )
    test_storage["careers"][career.id] = career

    kps = [
        {"id": "kp_1", "text": "Explains indexing", "weight": 0.5, "keywords": ["index", "b-tree"]},
        {"id": "kp_2", "text": "Discusses write performance tradeoff", "weight": 0.5, "keywords": ["tradeoff", "write"]},
    ]
    q = InterviewQuestion(
        id=uuid4(),
        career_id=career.id,
        type="technical",
        level="beginner",
        text="How do database indexes improve read performance, and what is the tradeoff?",
        key_points=kps,
        sample_answer="Indexes create B-tree structures speeding queries at the cost of slower writes.",
        status="verified",
    )
    test_storage["interview_questions"][q.id] = q

    sq = SessionQuestion(id=uuid4(), order=1, question_text=q.text, key_points=kps)
    now = datetime.now(timezone.utc)
    session = InterviewSession(
        id=uuid4(),
        user_id=user.id,
        career_id=career.id,
        type="technical",
        level="beginner",
        status="in_progress",
        started_at=now,
        expires_at=now + timedelta(minutes=30),
        session_questions=[sq],
    )
    test_storage["interview_sessions"][session.id] = session

    # Queue structured AI evaluation response with booleans only (NO numbers from AI)
    gateway = get_llm_gateway()
    mock_provider: MockLLMProvider = gateway.provider
    mock_provider.queue_response(
        json.dumps({
            "covered_points": {"kp_1": True, "kp_2": True},
            "strengths": ["Clear explanation of lookup structures", "Accurate indexing trade-off"],
            "improvements": ["Mention composite indexing"],
        })
    )

    ans_payload = {
        "session_question_id": str(sq.id),
        "answer_text": "Database indexes use balanced trees to provide logarithmic search time, but every insert requires updating the index structure.",
    }
    resp = await async_client.post(f"/v1/interviews/{session.id}/answers", json=ans_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Assert scoring method is AI and score was computed in code
    assert data["scoring_method"] == "ai"
    assert data["scores"]["coverage_score"] == 100
    assert data["scores"]["depth_score"] > 0
    assert data["scores"]["structure_score"] > 0
    assert "Clear explanation of lookup structures" in data["strengths"]


@pytest.mark.asyncio
async def test_ai_feature_wiring_portfolio_text_generation(async_client: AsyncClient, test_storage):
    """Integration: POST /v1/portfolio/generate-text executed through LLMGateway."""
    user = User(id=uuid4(), email="portfolio_ai@example.com", hashed_password="pw", role="student", is_active=True)
    test_storage["users"][user.id] = user
    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    gateway = get_llm_gateway()
    mock_provider: MockLLMProvider = gateway.provider
    mock_provider.queue_response(
        json.dumps({
            "generated_text": "AI-Synthesized about section focusing on high-throughput backend architecture.",
        })
    )

    payload = {
        "section": "about",
        "user_facts": ["Built asynchronous messaging service in Go", "Maintained 99.9% uptime"],
        "target_career": "Backend Engineer",
    }
    resp = await async_client.post("/v1/portfolio/generate-text", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "AI-Synthesized about section" in data["generated_text"]


@pytest.mark.asyncio
async def test_ai_feature_wiring_ai_chat(async_client: AsyncClient, test_storage):
    """Integration: POST /v1/ai/chat executed via LLMGateway with MockLLMProvider."""
    user = User(id=uuid4(), email="chat_ai@example.com", hashed_password="pw", role="student", is_active=True)
    test_storage["users"][user.id] = user
    profile = StudentProfile(id=uuid4(), user_id=user.id, name="Chat Student")
    test_storage["student_profiles"][profile.id] = profile
    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    gateway = get_llm_gateway()
    mock_provider: MockLLMProvider = gateway.provider
    mock_provider.queue_response(
        json.dumps({
            "answer": "AI-Generated advice: Focus on data structures and system design fundamentals.",
            "used_record_ids": [],
            "in_scope": True,
        })
    )

    payload = {
        "mode": "skills",
        "message": "What should I focus on for backend engineering?",
    }
    resp = await async_client.post("/v1/ai/chat", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["ai_status"] == "ok"
    assert "AI-Generated advice" in data["content"]


@pytest.mark.asyncio
async def test_telemetry_fallback_counter_tracking():
    """Telemetry: Per-feature fallback counts are recorded and tracked in telemetry summary."""
    reset_telemetry_counters()

    mock_provider = MockLLMProvider()
    gateway = LLMGateway(provider=mock_provider)

    # Queue an exception to force deterministic fallback activation
    mock_provider.queue_response(Exception("Simulated provider network timeout"))

    from pydantic import BaseModel

    class DummyOutput(BaseModel):
        generated_text: str

    res = await gateway.generate(
        prompt_name="portfolio_text",
        inputs={"section": "about", "target_career": "SWE", "user_facts": "Built APIs"},
        output_schema=DummyOutput,
        fallback=DummyOutput(generated_text="deterministic_fallback_text"),
        version=1,
    )

    assert res.telemetry.fallback_used is True
    assert res.data.generated_text == "deterministic_fallback_text"

    counts = get_fallback_counts()
    assert counts.get("portfolio_text") == 1
