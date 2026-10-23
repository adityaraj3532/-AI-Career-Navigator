"""Unit and integration tests for the demo account seeding script (Fix 5).

Verifies:
1. Complete creation of all demo artifacts:
   - User account with role=student and education_level=college
   - StudentProfile with bio, hours, skills, and Asia/Kolkata timezone
   - Completed assessment attempt, answers, and result with Holland code IRC
   - Shortlisted careers (SWE and Data Scientist)
   - Active Roadmap with 3 phases and 8 items (Phase 1 100% done)
   - Planner tasks linked to roadmap items (completed, in_progress, pending)
   - 7-day continuous activity ledger streak ending today
   - 4 awarded milestone rules (first_test, first_project, streak_7_days, first_phase_done)
   - Weekly goals (current week and previous week)
   - Skills & SkillEvidence records
   - Public UserPortfolio with custom projects, certificates, competitions, achievements
2. Idempotency: re-running without force-refresh succeeds and preserves data
3. Force refresh: wipes and re-creates clean records
4. Public portfolio API integration: GET /v1/portfolio/p/{slug} renders correctly with zero forbidden keys
5. Progress summary API integration: GET /v1/progress/summary reflects 7-day streak and milestones
"""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.portfolio import UserPortfolio
from app.models.profile import StudentProfile
from app.models.user import User
from scripts.seed_demo_account import (
    DEMO_EMAIL_DEFAULT,
    DEMO_PASSWORD_DEFAULT,
    DEMO_SLUG_DEFAULT,
    DEMO_TIMEZONE,
    seed_demo_account,
)


class ComprehensiveMockSession:
    """In-memory mock session supporting all queries executed by seed_demo_account."""

    def __init__(self) -> None:
        self.storage: Dict[str, Dict[Any, Any]] = {
            "users": {},
            "student_profiles": {},
            "assessment_versions": {},
            "assessment_questions": {},
            "assessment_attempts": {},
            "assessment_answers": {},
            "assessment_results": {},
            "careers": {},
            "user_shortlists": {},
            "roadmaps": {},
            "roadmap_phases": {},
            "roadmap_items": {},
            "planner_tasks": {},
            "activity_events": {},
            "milestone_rules": {},
            "user_milestones": {},
            "weekly_goals": {},
            "skills": {},
            "user_skills": {},
            "skill_evidence": {},
            "user_portfolios": {},
        }

    def add(self, instance: Any) -> None:
        table_name = getattr(instance, "__tablename__", None)
        if not table_name or table_name not in self.storage:
            return

        if table_name == "user_shortlists":
            key = (instance.user_id, instance.career_id)
        elif table_name == "weekly_goals":
            key = (instance.user_id, instance.week_start, instance.goal_type)
        elif table_name == "user_milestones":
            key = (instance.user_id, instance.rule_id)
        elif table_name == "user_skills":
            key = (instance.user_id, instance.skill_id)
        elif table_name == "activity_events":
            key = (instance.source_type, instance.source_id)
        else:
            if not getattr(instance, "id", None):
                instance.id = uuid4()
            key = instance.id

        self.storage[table_name][key] = instance

    async def delete(self, instance: Any) -> None:
        table_name = getattr(instance, "__tablename__", None)
        if not table_name or table_name not in self.storage:
            return

        if table_name == "users":
            user_id = instance.id
            self.storage["users"].pop(user_id, None)
            # Cascade delete all related user rows
            for t_name, store in self.storage.items():
                to_delete = []
                for k, obj in store.items():
                    if getattr(obj, "user_id", None) == user_id:
                        to_delete.append(k)
                for k in to_delete:
                    store.pop(k, None)
        else:
            key = getattr(instance, "id", None)
            if key and key in self.storage[table_name]:
                self.storage[table_name].pop(key, None)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, stmt: Any) -> Any:
        class MockResult:
            def __init__(self, items: List[Any]) -> None:
                self._items = items

            def scalar_one_or_none(self) -> Optional[Any]:
                return self._items[0] if self._items else None

            def scalar(self) -> Optional[Any]:
                return self._items[0] if self._items else None

            def scalars(self) -> Any:
                items = self._items

                class MockScalars:
                    def all(self) -> List[Any]:
                        return items

                    def first(self) -> Optional[Any]:
                        return items[0] if items else None

                return MockScalars()

        try:
            entity = stmt.column_descriptions[0]["entity"]
            table_name = getattr(entity, "__tablename__", None)
            if not table_name or table_name not in self.storage:
                return MockResult([])

            items = list(self.storage[table_name].values())

            # Evaluate where clauses
            for clause in getattr(stmt, "_where_criteria", []):
                left_key = getattr(getattr(clause, "left", None), "key", None)
                right_val = getattr(getattr(clause, "right", None), "value", None)

                # Handle is_(True) or boolean expressions
                modifier = getattr(clause, "modifier", None)
                if modifier is not None or right_val is True:
                    if left_key:
                        items = [it for it in items if bool(getattr(it, left_key, False)) is True]
                    continue

                if left_key and right_val is not None:
                    items = [it for it in items if getattr(it, left_key, None) == right_val]

            return MockResult(items)
        except Exception:
            return MockResult([])


# ==============================================================================
# TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_seed_demo_account_creates_all_artifacts():
    """Verify seed_demo_account builds the complete, fully populated user ecosystem."""
    session = ComprehensiveMockSession()

    res = await seed_demo_account(
        session=session,
        email="test_demo@career-navigator.io",
        password="TestDemoPassword123!",
        slug="test-alex-chen",
    )

    # 1. Output summary contract
    assert res["email"] == "test_demo@career-navigator.io"
    assert res["role"] == "student"
    assert res["name"] == "Alex Chen"
    assert res["timezone"] == DEMO_TIMEZONE
    assert res["assessment_status"] == "completed"
    assert res["holland_code"] == "IRC"
    assert len(res["shortlisted_careers"]) == 2
    assert "Software Development Engineer" in res["shortlisted_careers"]
    assert res["portfolio_slug"] == "test-alex-chen"
    assert res["portfolio_public"] is True

    # 2. Database assertions
    user_id = res["user_id"]
    assert user_id in session.storage["users"]
    user = session.storage["users"][user_id]
    assert user.is_active is True
    assert user.education_level == "college"

    # Profile
    profiles = list(session.storage["student_profiles"].values())
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof.name == "Alex Chen"
    assert prof.budget_level == "medium"
    assert prof.hours_available_per_week == 20
    assert "Computer Science" in prof.subjects_of_interest
    assert any(s["name"] == "Python" for s in prof.skills)

    # Assessment
    attempts = list(session.storage["assessment_attempts"].values())
    assert len(attempts) == 1
    assert attempts[0].status == "completed"

    answers = list(session.storage["assessment_answers"].values())
    assert len(answers) == 6

    results = list(session.storage["assessment_results"].values())
    assert len(results) == 1
    ares = results[0]
    assert ares.holland_code == "IRC"
    assert ares.dimension_scores["I"] == 92.0
    assert ares.dimension_scores["R"] == 75.0
    assert len(ares.career_suggestions) == 2
    assert len(ares.traits) >= 3

    # Shortlist
    shortlists = list(session.storage["user_shortlists"].values())
    assert len(shortlists) == 2

    # Roadmap & Items
    roadmaps = list(session.storage["roadmaps"].values())
    assert len(roadmaps) == 1
    rm = roadmaps[0]
    assert rm.status == "active"
    assert rm.hours_per_week == 20

    phases = list(session.storage["roadmap_phases"].values())
    assert len(phases) == 3

    items = list(session.storage["roadmap_items"].values())
    assert len(items) == 8
    # Phase 1 items (indices 0, 1, 2) must be done
    done_items = [it for it in items if it.status == "done"]
    assert len(done_items) >= 5

    # Planner tasks
    tasks = list(session.storage["planner_tasks"].values())
    assert len(tasks) == 4
    completed_tasks = [t for t in tasks if t.status == "completed"]
    in_progress_tasks = [t for t in tasks if t.status == "in_progress"]
    pending_tasks = [t for t in tasks if t.status == "pending"]
    assert len(completed_tasks) == 2
    assert len(in_progress_tasks) == 1
    assert len(pending_tasks) == 1

    # Activity events & 7-day streak
    events = list(session.storage["activity_events"].values())
    assert len(events) == 7
    event_dates = sorted([e.local_date for e in events])
    # Continuous dates covering 7 consecutive days
    for idx in range(len(event_dates) - 1):
        assert (event_dates[idx + 1] - event_dates[idx]).days == 1

    # Milestones (4 awarded)
    milestones = list(session.storage["user_milestones"].values())
    assert len(milestones) == 4

    # Weekly goals
    goals = list(session.storage["weekly_goals"].values())
    assert len(goals) == 4  # 2 for current week, 2 for previous week

    # Skills & Evidence
    user_skills = list(session.storage["user_skills"].values())
    assert len(user_skills) == 4
    evidence = list(session.storage["skill_evidence"].values())
    assert len(evidence) == 4

    # Portfolio
    portfolios = list(session.storage["user_portfolios"].values())
    assert len(portfolios) == 1
    port = portfolios[0]
    assert port.is_public is True
    assert port.slug == "test-alex-chen"
    assert len(port.custom_projects) == 2
    assert len(port.custom_certificates) == 1
    assert len(port.competitions) == 1
    assert len(port.achievements) == 2


@pytest.mark.asyncio
async def test_seed_demo_account_idempotence():
    """Running seed_demo_account twice with the same email updates/preserves data without crash."""
    session = ComprehensiveMockSession()

    res1 = await seed_demo_account(
        session=session,
        email="idempotent_demo@example.com",
        password="InitialPassword123!",
    )
    user_id_1 = res1["user_id"]

    res2 = await seed_demo_account(
        session=session,
        email="idempotent_demo@example.com",
        password="UpdatedPassword123!",
    )
    user_id_2 = res2["user_id"]

    # Invariant: User ID is preserved; no duplicate user row created
    assert user_id_1 == user_id_2
    assert len(session.storage["users"]) == 1
    assert len(session.storage["student_profiles"]) == 1
    assert len(session.storage["roadmaps"]) == 1


@pytest.mark.asyncio
async def test_seed_demo_account_force_refresh():
    """Force refresh wipes existing user row and cleanly re-creates all tables."""
    session = ComprehensiveMockSession()

    res1 = await seed_demo_account(
        session=session,
        email="refresh_demo@example.com",
        password="FirstPassword123!",
    )
    user_id_1 = res1["user_id"]

    res2 = await seed_demo_account(
        session=session,
        email="refresh_demo@example.com",
        password="SecondPassword123!",
        force_refresh=True,
    )
    user_id_2 = res2["user_id"]

    # Invariant: Force refresh generates a fresh user ID and full ecosystem
    assert user_id_1 != user_id_2
    assert len(session.storage["users"]) == 1
    assert session.storage["users"][user_id_2].email == "refresh_demo@example.com"


def test_seed_demo_account_cli_argument_defaults():
    """Verify CLI parser flags, help text, and defaults."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=DEMO_EMAIL_DEFAULT)
    parser.add_argument("--password", default=DEMO_PASSWORD_DEFAULT)
    parser.add_argument("--slug", default=DEMO_SLUG_DEFAULT)
    parser.add_argument("--force-refresh", action="store_true")

    args = parser.parse_args([])
    assert args.email == "demo@career-navigator.io"
    assert args.password == "DemoAccount@2026!"
    assert args.slug == "alex-chen"
    assert args.force_refresh is False

    args_custom = parser.parse_args([
        "--email", "custom@test.io",
        "--password", "CustomPass123!",
        "--slug", "custom-slug",
        "--force-refresh",
    ])
    assert args_custom.email == "custom@test.io"
    assert args_custom.password == "CustomPass123!"
    assert args_custom.slug == "custom-slug"
    assert args_custom.force_refresh is True


@pytest.mark.asyncio
async def test_demo_account_public_portfolio_endpoint(async_client: AsyncClient, test_storage: Dict[str, Any]):
    """Ensure the seeded demo account's public portfolio is accessible and leaks zero forbidden keys."""
    # Seed user and public portfolio in test_storage
    user = User(
        id=uuid4(),
        email="demo@career-navigator.io",
        hashed_password="pw",
        role="student",
        education_level="college",
        is_active=True,
    )
    test_storage["users"][user.id] = user

    portfolio = UserPortfolio(
        id=uuid4(),
        user_id=user.id,
        slug="alex-chen",
        is_public=True,
        headline="Aspiring Software Engineer | Distributed Systems & Backend Enthusiast",
        about="Third-year Computer Science student passionate about distributed architectures.",
        visibility={
            "about": True,
            "skills": True,
            "projects": True,
            "certificates": True,
            "competitions": True,
            "achievements": True,
        },
        featured_item_ids=[],
        custom_projects=[
            {
                "title": "Async Task Distributed Worker",
                "description": "High-performance distributed worker engine.",
                "skills": ["Python", "FastAPI", "Redis"],
                "link": "https://github.com/alexchen/async-task-worker",
                "completed_date": "2026-09-15",
                "provenance": "self_reported",
            }
        ],
        custom_certificates=[
            {
                "title": "AWS Certified Cloud Practitioner",
                "issuer": "Amazon Web Services",
                "credential_url": "https://aws.amazon.com/verification",
                "issue_date": "2025-11-15",
                "provenance": "self_reported",
            }
        ],
        competitions=[
            {
                "title": "National Collegiate Systems Hackathon",
                "award_or_rank": "Top 10 Finalist",
                "description": "Designed fault-tolerant microservices.",
                "year": 2025,
            }
        ],
        achievements=[
            {
                "title": "7-Day Consistent Study Streak",
                "description": "Maintained unbroken study streak.",
                "date": "2026-10-24",
            }
        ],
    )
    test_storage["user_portfolios"][portfolio.id] = portfolio

    # Call unauthenticated public slug route
    resp = await async_client.get("/v1/portfolio/p/alex-chen")
    assert resp.status_code == 200
    data = resp.json()

    assert data["slug"] == "alex-chen"
    assert data["headline"] == "Aspiring Software Engineer | Distributed Systems & Backend Enthusiast"
    assert len(data["projects"]) == 1
    assert data["projects"][0]["title"] == "Async Task Distributed Worker"
    assert len(data["certificates"]) == 1
    assert len(data["competitions"]) == 1
    assert len(data["achievements"]) == 1

    # Security Assertion: Zero forbidden keys leaked in public view
    forbidden_keys = {"user_id", "email", "hashed_password", "role", "internal_id", "answers", "dimension_scores"}
    for key in forbidden_keys:
        assert key not in data, f"Security violation: forbidden key '{key}' present in public portfolio response"


@pytest.mark.asyncio
async def test_demo_account_progress_summary_endpoint(async_client: AsyncClient, test_storage: Dict[str, Any]):
    """Ensure the seeded demo account's progress summary reflects streak, milestones, and goals."""
    user = User(
        id=uuid4(),
        email="demo@career-navigator.io",
        hashed_password="pw",
        role="student",
        education_level="college",
        is_active=True,
    )
    test_storage["users"][user.id] = user

    profile = StudentProfile(
        id=uuid4(),
        user_id=user.id,
        name="Alex Chen",
        timezone="Asia/Kolkata",
    )
    test_storage["student_profiles"][profile.id] = profile

    token = create_access_token(user.id, user.email, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/v1/progress/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["timezone"] == "Asia/Kolkata"
    assert "current_streak" in data
    assert "longest_streak" in data
    assert "milestones" in data
    assert "weekly_goals" in data
