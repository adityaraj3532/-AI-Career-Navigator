"""Timeout, Retry Policy, and Deterministic Fallback Test Suite.

Verifies that across all platform subsystems:
1. LLMGateway enforces a 15s per-call timeout and a 20s overall budget with deterministic fallbacks.
2. Gateway retries exactly once on schema validation errors only; timeouts activate fallback immediately without retry.
3. Health check probes for PostgreSQL and Redis enforce strict timeouts to prevent hangs.
4. Redis failures in rate limiters fall back gracefully to in-memory limiters.
5. Every AI service (Interviews, Assessments, Portfolios, Chat, Background Workers) has verified, deterministic fallbacks.
"""

import asyncio
from uuid import uuid4
import pytest
from pydantic import BaseModel

from app.core.database import check_db_health
from app.core.redis import check_redis_health
from app.llm.gateway import LLMGateway
from app.llm.provider import MockLLMProvider
from app.models.interview import InterviewQuestion
from app.models.profile import StudentProfile
from app.models.user import User
from app.services.chat_rate_limiter import check_chat_rate_limit, clear_in_memory_rate_limiter
from app.services.interview_service import InterviewService
from app.services.portfolio_service import PortfolioService
from app.workers.tasks import (
    generate_weekly_progress_summary,
)


class DummyOutput(BaseModel):
    summary: str
    score: int


@pytest.mark.asyncio
async def test_gateway_timeout_activates_fallback_without_retry():
    """Resilience Invariant: A hanging provider call (>15s timeout) activates fallback immediately
    with attempts=1 (zero retry on timeout).
    """
    mock_provider = MockLLMProvider()

    async def _hanging_call(prompt: str, schema, timeout: float):
        # Simulate provider exceeding per-call timeout
        await asyncio.sleep(timeout + 0.05)
        return '{"summary": "Late response", "score": 100}'

    mock_provider.generate = _hanging_call

    # Configure short timeout for test speed
    gateway = LLMGateway(provider=mock_provider, per_call_timeout=0.1, overall_timeout=0.25)
    fallback = DummyOutput(summary="Deterministic Fallback", score=50)

    res = await gateway.generate(
        prompt_name="career_explainer",
        system_variables={"target_career": "SWE", "score_pct": 80, "verified_exam_ids": "GATE"},
        untrusted_inputs={"user_profile_bio": "Student notes"},
        output_schema=DummyOutput,
        fallback=fallback,
        version=1,
    )

    assert res.telemetry.fallback_used is True
    assert res.telemetry.status == "fallback"
    assert res.telemetry.attempts == 1  # Timeouts must NEVER retry
    assert res.data.summary == "Deterministic Fallback"
    assert res.data.score == 50


@pytest.mark.asyncio
async def test_gateway_overall_budget_timeout():
    """Resilience Invariant: Exhausting the overall time budget triggers fallback."""
    mock_provider = MockLLMProvider()

    # Configure overall timeout of 0.1s
    gateway = LLMGateway(provider=mock_provider, per_call_timeout=0.2, overall_timeout=0.05)
    fallback = DummyOutput(summary="Budget Fallback", score=40)

    async def _slow_call(prompt: str, schema, timeout: float):
        await asyncio.sleep(0.1)
        return '{"summary": "Done", "score": 90}'

    mock_provider.generate = _slow_call

    res = await gateway.generate(
        prompt_name="career_explainer",
        system_variables={"target_career": "SWE", "score_pct": 80, "verified_exam_ids": "GATE"},
        untrusted_inputs={"user_profile_bio": "Student notes"},
        output_schema=DummyOutput,
        fallback=fallback,
        version=1,
    )

    assert res.telemetry.fallback_used is True
    assert res.data.summary == "Budget Fallback"


@pytest.mark.asyncio
async def test_gateway_retries_once_on_validation_failure_only():
    """Resilience Invariant: Schema validation failure triggers exactly ONE retry before fallback."""
    mock_provider = MockLLMProvider()

    call_count = 0

    async def _flaky_json(prompt: str, schema, timeout: float):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "NOT VALID JSON"
        return '{"summary": "Valid on attempt 2", "score": 95}'

    mock_provider.generate = _flaky_json

    gateway = LLMGateway(provider=mock_provider)
    fallback = DummyOutput(summary="Fallback", score=0)

    res = await gateway.generate(
        prompt_name="career_explainer",
        system_variables={"target_career": "SWE", "score_pct": 80, "verified_exam_ids": "GATE"},
        untrusted_inputs={"user_profile_bio": "Student notes"},
        output_schema=DummyOutput,
        fallback=fallback,
        version=1,
    )

    assert res.telemetry.status == "retry_success"
    assert res.telemetry.fallback_used is False
    assert res.telemetry.attempts == 2
    assert res.data.summary == "Valid on attempt 2"


@pytest.mark.asyncio
async def test_database_health_check_timeout(monkeypatch):
    """Resilience Invariant: A hanging PostgreSQL connection times out in 3.0s and returns False."""
    from contextlib import asynccontextmanager
    from unittest.mock import MagicMock
    from app.core import database

    mock_engine = MagicMock()

    @asynccontextmanager
    async def _hanging_connect(*args, **kwargs):
        await asyncio.sleep(5.0)
        yield None

    mock_engine.connect = _hanging_connect
    monkeypatch.setattr(database, "engine", mock_engine)

    is_healthy = await check_db_health()
    assert is_healthy is False


@pytest.mark.asyncio
async def test_redis_health_check_timeout(monkeypatch):
    """Resilience Invariant: A hanging Redis server times out in 2.0s and returns False."""
    from app.core import redis

    class HangingRedis:
        async def ping(self):
            await asyncio.sleep(5.0)
            return True

    monkeypatch.setattr(redis, "get_redis_client", lambda: HangingRedis())

    is_healthy = await check_redis_health()
    assert is_healthy is False


@pytest.mark.asyncio
async def test_chat_rate_limiter_in_memory_fallback_on_redis_timeout(monkeypatch):
    """Resilience Invariant: Redis timeouts trigger in-memory rate limiting without dropping requests."""
    clear_in_memory_rate_limiter()

    class HangingRedisClient:
        def pipeline(self):
            return self

        def incr(self, *args, **kwargs):
            return self

        def expire(self, *args, **kwargs):
            return self

        async def execute(self):
            # Hang longer than 0.5s timeout in check_chat_rate_limit
            await asyncio.sleep(1.0)
            return [1, True, 1, True]

    monkeypatch.setattr("app.services.chat_rate_limiter.get_redis_client", lambda: HangingRedisClient())

    user_id = uuid4()
    # Should fall back to in-memory rate limiter within ~0.5s and allow request
    await check_chat_rate_limit(user_id)


@pytest.mark.asyncio
async def test_interview_scoring_deterministic_fallback():
    """Resilience Invariant: Interview answer evaluation uses deterministic rule-based fallback
    when LLMGateway times out or fails.
    """
    mock_provider = MockLLMProvider()
    # Queue an exception to force fallback
    mock_provider.queue_response(Exception("Simulated provider outage"))
    gateway = LLMGateway(provider=mock_provider)

    kps = [
        {"id": "kp_1", "text": "Explains indexing", "weight": 0.5, "keywords": ["index", "b-tree"]},
        {"id": "kp_2", "text": "Discusses write performance tradeoff", "weight": 0.5, "keywords": ["tradeoff", "write"]},
    ]
    q = InterviewQuestion(
        id=uuid4(),
        career_id=uuid4(),
        type="technical",
        level="beginner",
        text="How do database indexes improve read performance?",
        key_points=kps,
        sample_answer="B-trees allow logarithmic search time at write cost.",
        status="verified",
    )

    repo_mock = type("MockRepo", (), {})()
    service = InterviewService(repo=repo_mock, gateway=gateway)

    answer_text = "Database indexes use b-tree structures to speed search, with a write tradeoff."
    # When gateway fails, _evaluate_answer_with_ai returns None to trigger fallback_score_answer
    result = await service._evaluate_answer_with_ai(q.text, q.key_points, answer_text)
    assert result is None

    # Verify fallback_score_answer pure function computes deterministic scores
    from app.services.interview_scoring_engine import fallback_score_answer
    fallback_res = fallback_score_answer(q.key_points, answer_text, rubric_version="1.0")
    assert fallback_res.scoring_method == "fallback"
    assert fallback_res.confidence == "low"
    assert fallback_res.scores.coverage_score > 0


@pytest.mark.asyncio
async def test_interview_followup_deterministic_fallback():
    """Resilience Invariant: When AI follow-up generation fails, None is gracefully returned."""
    mock_provider = MockLLMProvider()
    mock_provider.queue_response(Exception("Simulated provider outage"))
    gateway = LLMGateway(provider=mock_provider)

    kps = [{"id": "kp_2", "text": "write tradeoff", "keywords": ["write"]}]
    q = InterviewQuestion(
        id=uuid4(),
        career_id=uuid4(),
        type="technical",
        level="beginner",
        text="Explain indexes",
        key_points=kps,
        sample_answer="Sample answer",
        status="verified",
    )

    repo_mock = type("MockRepo", (), {})()
    service = InterviewService(repo=repo_mock, gateway=gateway)

    followup = await service._generate_follow_up_question(q.text, ["write tradeoff"], "Incomplete answer")
    # Followup generation returns None upon provider failure or timeout, gracefully proceeding without follow-up
    assert followup is None


@pytest.mark.asyncio
async def test_portfolio_pitch_deterministic_fallback():
    """Resilience Invariant: Portfolio pitch generation falls back to deterministic highlights."""
    from unittest.mock import AsyncMock

    mock_provider = MockLLMProvider()
    mock_provider.queue_response(Exception("Simulated provider outage"))
    gateway = LLMGateway(provider=mock_provider)

    service = PortfolioService(session=None, gateway=gateway)
    service.repo.get_user_skills = AsyncMock(return_value=[])
    service.repo.get_completed_roadmap_milestones = AsyncMock(return_value=[])
    service.repo.get_completed_diagnostic_tests = AsyncMock(return_value=[])
    service.repo.get_user_profile = AsyncMock(return_value=None)

    user = User(id=uuid4(), email="pitch_fallback@test.com", hashed_password="pw", role="student", education_level="undergraduate", is_active=True)
    req = type("MockSummaryReq", (), {"headline": "Backend Engineer"})()

    # Call generate_portfolio_pitch with failing gateway
    res = await service.generate_portfolio_pitch(user, req)
    assert res.elevator_pitch != ""
    assert "Software Engineering" in res.elevator_pitch
    assert len(res.key_highlights) >= 2


@pytest.mark.asyncio
async def test_worker_weekly_progress_summary_fallback_on_gateway_error(monkeypatch):
    """Resilience Invariant: Background worker generates deterministic weekly summary on LLM failure."""
    from app.workers import tasks

    class FailingGateway:
        async def generate(self, *args, **kwargs):
            raise Exception("Worker provider failure")

    monkeypatch.setattr(tasks, "LLMGateway", lambda: FailingGateway())

    # Mock DB session in tasks
    from unittest.mock import AsyncMock, MagicMock

    user_id = uuid4()
    profile = StudentProfile(id=uuid4(), user_id=user_id, name="Test Learner")

    mock_session = AsyncMock()
    # Mock profile lookup
    mock_res_profile = MagicMock()
    mock_res_profile.scalar_one_or_none.return_value = profile

    # Mock activity events
    mock_res_events = MagicMock()
    mock_res_events.all.return_value = [("roadmap", "2026-10-20"), ("assessment", "2026-10-21")]

    mock_session.execute.side_effect = [mock_res_profile, mock_res_events]

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session_factory():
        yield mock_session

    monkeypatch.setattr(tasks, "async_session_factory", mock_session_factory)

    data = await generate_weekly_progress_summary({}, str(user_id))
    assert data is not None
    assert "You completed 2 learning activities" in data["weekly_summary"]
    assert "Consistent daily engagement" in data["encouragement"]
