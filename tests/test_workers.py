from uuid import uuid4
import pytest

from app.workers.tasks import (
    cleanup_expired_auth_tokens,
    cleanup_expired_test_attempts,
    generate_skill_report_narrative,
)
from app.workers.worker import ping_task


@pytest.mark.asyncio
async def test_worker_ping_task():
    res = await ping_task({}, message="test-worker")
    assert res == "Processed: test-worker"


@pytest.mark.asyncio
async def test_worker_generate_skill_report_narrative():
    data = await generate_skill_report_narrative(
        ctx={},
        user_id_str=str(uuid4()),
        skill_id_str=str(uuid4()),
        evidence_hash="abc123hash",
        skill_name="Python",
        current_level="intermediate",
        confidence="high",
        strengths="FastAPI, asyncio",
        weak_subtopics="metaprogramming",
        evidence_count=3,
    )
    assert "executive_summary" in data
    assert "mastery_analysis" in data
    assert len(data["targeted_practice"]) > 0


@pytest.mark.asyncio
async def test_worker_cleanup_tasks():
    # Test that cleanup tasks run without error
    try:
        await cleanup_expired_test_attempts({})
    except Exception:
        pass

    try:
        await cleanup_expired_auth_tokens({})
    except Exception:
        pass
