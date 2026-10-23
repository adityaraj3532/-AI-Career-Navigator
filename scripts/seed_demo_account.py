"""Seed script for a complete realistic demo user account.

Seeds:
- User (role=student, education_level=college)
- StudentProfile (name, budget_level, hours_per_week, subjects_of_interest, skills, timezone)
- Completed Assessment (version, attempt, answers, scoring result with Holland code and RIASEC weights)
- Shortlisted Careers (SWE, Data Scientist)
- Active Roadmap (phases, completed and in-progress items, planner tasks)
- Progress Ledger (7-day activity streak, 4 awarded milestone rules, weekly goals)
- Skills & Evidence (UserSkill levels, SkillEvidence records)
- Public Portfolio (slug, bio, custom projects, certificates, competitions, achievements)

Usage:
    python -m scripts.seed_demo_account [--email EMAIL] [--password PASSWORD] [--slug SLUG] [--force-refresh]
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import sys
from typing import Any, Dict
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.assessment import (
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentResult,
    AssessmentVersion,
)
from app.models.career import Career, UserShortlist
from app.models.planner import PlannerTask
from app.models.portfolio import UserPortfolio
from app.models.profile import StudentProfile
from app.models.progress import (
    ActivityEvent,
    MilestoneRule,
    UserMilestone,
    WeeklyGoal,
)
from app.models.roadmap import (
    Roadmap,
    RoadmapItem,
    RoadmapPhase,
)
from app.models.skill import Skill, SkillEvidence, UserSkill
from app.models.user import User
from app.services.activity_service import seed_milestones
from app.services.progress_engine import compute_local_date, get_week_monday

logger = logging.getLogger("scripts.seed_demo_account")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


DEMO_EMAIL_DEFAULT = "demo@career-navigator.io"
DEMO_PASSWORD_DEFAULT = "DemoAccount@2026!"
DEMO_SLUG_DEFAULT = "alex-chen"
DEMO_TIMEZONE = "Asia/Kolkata"


async def ensure_catalog_prerequisites(session: AsyncSession) -> Dict[str, Any]:
    """Ensure baseline careers, skills, assessment version, and milestone rules exist."""
    # 1. Milestone rules
    seeded_rules = await seed_milestones(session)
    logger.info("Ensured %d milestone rules seeded.", len(seeded_rules))

    # 2. Careers: SWE and DATA_SCIENTIST
    careers: Dict[str, Career] = {}
    for code, title, weights, overview in [
        (
            "SWE",
            "Software Development Engineer",
            {"R": 70, "I": 90, "A": 50, "S": 30, "E": 40, "C": 75},
            "Designs, implements, and maintains scalable software applications, backend services, and distributed systems.",
        ),
        (
            "DATA_SCIENTIST",
            "Data Scientist & Machine Learning Engineer",
            {"R": 50, "I": 95, "A": 40, "S": 25, "E": 35, "C": 80},
            "Applies statistical algorithms, machine learning models, and deep data analysis to discover predictive patterns.",
        ),
    ]:
        stmt = select(Career).where(Career.code == code)
        res = await session.execute(stmt)
        c = res.scalar_one_or_none()
        if not c:
            c = Career(
                id=uuid4(),
                code=code,
                title=title,
                cluster="Information Technology",
                aliases=["Software Engineer", "Backend Developer"] if code == "SWE" else ["ML Engineer"],
                overview=overview,
                status="verified",
                source_url=f"https://www.onetonline.org/find/quick?s={code}",
                dimension_weights=weights,
                required_skills=[
                    {"name": "Python", "level": "advanced"},
                    {"name": "PostgreSQL", "level": "intermediate"},
                ],
                education_paths=[
                    {"stage": "Undergraduate", "stream": "Computer Science", "degree": "B.Tech / B.S.", "description": "Core computer science and algorithms."}
                ],
            )
            session.add(c)
            await session.flush()
            logger.info("Created prerequisite career: %s (%s)", title, code)
        careers[code] = c

    # 3. Skills: Python, PostgreSQL, FastAPI, Docker, Algorithms
    skills: Dict[str, Skill] = {}
    for sk_slug, name, category in [
        ("python", "Python", "Languages"),
        ("postgresql", "PostgreSQL", "Databases"),
        ("fastapi", "FastAPI", "Backend"),
        ("docker", "Docker", "DevOps"),
        ("algorithms", "Algorithms & Data Structures", "Computer Science"),
    ]:
        stmt = select(Skill).where(Skill.slug == sk_slug)
        res = await session.execute(stmt)
        s = res.scalar_one_or_none()
        if not s:
            s = Skill(
                id=uuid4(),
                slug=sk_slug,
                name=name,
                category=category,
                description=f"Core technical competency in {name}.",
                aliases=[name.lower()],
            )
            session.add(s)
            await session.flush()
            logger.info("Created prerequisite skill: %s", name)
        skills[sk_slug] = s

    # 4. Assessment Version & Questions
    stmt_v = select(AssessmentVersion).where(AssessmentVersion.version_number == 1)
    res_v = await session.execute(stmt_v)
    version = res_v.scalar_one_or_none()
    if not version:
        version = AssessmentVersion(
            id=uuid4(),
            version_number=1,
            title="Standard RIASEC Career Vocational Assessment",
            description="Comprehensive vocational interest profiling based on Holland codes.",
            is_active=True,
        )
        session.add(version)
        await session.flush()

        # Add 6 questions (one per Holland dimension)
        dimensions = [
            ("R", "I enjoy assembling electronic devices or building physical hardware prototypes."),
            ("I", "I enjoy analyzing complex algorithmic problems and mathematical proofs."),
            ("A", "I like designing novel user interface layouts and creative digital artwork."),
            ("S", "I enjoy mentoring junior students and explaining technical concepts."),
            ("E", "I like pitching technical startup ideas and leading engineering project teams."),
            ("C", "I prefer maintaining organized code architectures and systematic documentation."),
        ]
        for order, (dim, text) in enumerate(dimensions, start=1):
            q = AssessmentQuestion(
                id=uuid4(),
                assessment_version_id=version.id,
                question_order=order,
                text=text,
                dimension=dim,
                reverse_scored=False,
                is_active=True,
            )
            session.add(q)
        await session.flush()
        logger.info("Created prerequisite AssessmentVersion v1 with 6 questions.")

    return {
        "careers": careers,
        "skills": skills,
        "assessment_version": version,
    }


async def seed_demo_account(
    session: AsyncSession,
    email: str = DEMO_EMAIL_DEFAULT,
    password: str = DEMO_PASSWORD_DEFAULT,
    slug: str = DEMO_SLUG_DEFAULT,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Seed or update the comprehensive demo account."""
    clean_email = email.strip().lower()
    now_utc = datetime.now(timezone.utc)
    today_local = compute_local_date(now_utc, DEMO_TIMEZONE)

    # 1. Ensure master prerequisites exist
    prereqs = await ensure_catalog_prerequisites(session)
    careers = prereqs["careers"]
    skills = prereqs["skills"]
    assessment_version: AssessmentVersion = prereqs["assessment_version"]

    # 2. Check for existing user
    stmt_user = select(User).where(User.email == clean_email)
    res_user = await session.execute(stmt_user)
    existing_user = res_user.scalar_one_or_none()

    if existing_user and force_refresh:
        logger.info("Force refresh specified: deleting existing demo user %s (%s)", clean_email, existing_user.id)
        # Cascades to student_profiles, assessment_attempts, roadmaps, portfolios, etc.
        await session.delete(existing_user)
        await session.flush()
        existing_user = None

    if existing_user:
        logger.info("Demo user '%s' already exists (ID: %s). Updating records...", clean_email, existing_user.id)
        user = existing_user
        user.hashed_password = hash_password(password)
        user.is_active = True
        user.education_level = "college"
        user.role = "student"
    else:
        logger.info("Creating new demo user account: %s", clean_email)
        user = User(
            id=uuid4(),
            email=clean_email,
            hashed_password=hash_password(password),
            role="student",
            education_level="college",
            is_active=True,
            created_at=now_utc - timedelta(days=14),
            updated_at=now_utc,
        )
        session.add(user)
        await session.flush()

    # 3. Student Profile
    stmt_profile = select(StudentProfile).where(StudentProfile.user_id == user.id)
    res_profile = await session.execute(stmt_profile)
    profile = res_profile.scalar_one_or_none()

    profile_data = {
        "name": "Alex Chen",
        "budget_level": "medium",
        "hours_available_per_week": 20,
        "subjects_of_interest": ["Computer Science", "Artificial Intelligence", "Web Development", "Cloud Systems"],
        "skills": [
            {"name": "Python", "level": "intermediate"},
            {"name": "PostgreSQL", "level": "intermediate"},
            {"name": "FastAPI", "level": "intermediate"},
            {"name": "System Design", "level": "beginner"},
        ],
        "timezone": DEMO_TIMEZONE,
    }

    if profile:
        for k, v in profile_data.items():
            setattr(profile, k, v)
        profile.updated_at = now_utc
    else:
        profile = StudentProfile(
            id=uuid4(),
            user_id=user.id,
            **profile_data,
            created_at=now_utc - timedelta(days=14),
            updated_at=now_utc,
        )
        session.add(profile)
    await session.flush()

    # 4. Completed Assessment (Attempt + Answers + Result)
    # Check if user already has an attempt
    stmt_attempt = (
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.user_id == user.id,
            AssessmentAttempt.assessment_version_id == assessment_version.id,
        )
    )
    res_attempt = await session.execute(stmt_attempt)
    attempt = res_attempt.scalar_one_or_none()

    if not attempt:
        attempt = AssessmentAttempt(
            id=uuid4(),
            user_id=user.id,
            assessment_version_id=assessment_version.id,
            status="completed",
            started_at=now_utc - timedelta(days=14),
            submitted_at=now_utc - timedelta(days=14),
            updated_at=now_utc - timedelta(days=14),
        )
        session.add(attempt)
        await session.flush()

        # Answers
        stmt_qs = select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_version_id == assessment_version.id
        )
        res_qs = await session.execute(stmt_qs)
        questions = res_qs.scalars().all()

        answer_ratings = {"R": 4, "I": 5, "A": 3, "S": 3, "E": 3, "C": 4}
        for q in questions:
            ans = AssessmentAnswer(
                id=uuid4(),
                attempt_id=attempt.id,
                question_id=q.id,
                value=answer_ratings.get(q.dimension, 4),
                updated_at=now_utc - timedelta(days=14),
            )
            session.add(ans)

    # Assessment Result
    stmt_res = select(AssessmentResult).where(AssessmentResult.user_id == user.id)
    res_res = await session.execute(stmt_res)
    result_record = res_res.scalar_one_or_none()

    swe_career = careers["SWE"]
    ds_career = careers["DATA_SCIENTIST"]

    result_data = {
        "user_id": user.id,
        "attempt_id": attempt.id,
        "assessment_version_id": assessment_version.id,
        "version": assessment_version.version_number,
        "dimension_scores": {"R": 75.0, "I": 92.0, "A": 65.0, "S": 58.0, "E": 60.0, "C": 80.0},
        "holland_code": "IRC",
        "holland_code_label": "Investigative / Realistic / Conventional",
        "traits": [
            "Analytical problem-solver",
            "Systems thinker",
            "Independent researcher",
            "Data-driven builder",
        ],
        "skills": [
            "Python",
            "Backend Engineering",
            "Algorithms & Data Structures",
            "Relational Databases",
            "Async Programming",
        ],
        "recommended_streams": [
            "Software Engineering",
            "Artificial Intelligence & Distributed Systems",
        ],
        "career_suggestions": [
            {
                "career_id": str(swe_career.id),
                "career_title": swe_career.title,
                "similarity_score": 0.95,
                "reason": "High investigative orientation and systematic problem-solving aptitude strongly align with software engineering requirements.",
            },
            {
                "career_id": str(ds_career.id),
                "career_title": ds_career.title,
                "similarity_score": 0.89,
                "reason": "Strong analytical and data-driven traits make machine learning systems and data architecture a compelling match.",
            },
        ],
        "ai_explanation": (
            "Your assessment reveals an exceptional alignment between Investigative analytical thinking "
            "and Realistic hands-on engineering execution. You excel at deconstructing complex technical "
            "problems into structured components and implementing robust, data-backed software solutions."
        ),
        "disclaimer_note": (
            "These results provide career navigation guidance and vocational exploration insights; "
            "they are not a psychological evaluation or clinical diagnosis."
        ),
    }

    if result_record:
        for k, v in result_data.items():
            setattr(result_record, k, v)
    else:
        result_record = AssessmentResult(
            id=uuid4(),
            **result_data,
            created_at=now_utc - timedelta(days=14),
        )
        session.add(result_record)
    await session.flush()

    # 5. Career Shortlist
    for c in [swe_career, ds_career]:
        stmt_short = select(UserShortlist).where(
            UserShortlist.user_id == user.id,
            UserShortlist.career_id == c.id,
        )
        res_short = await session.execute(stmt_short)
        if not res_short.scalar_one_or_none():
            session.add(
                UserShortlist(
                    user_id=user.id,
                    career_id=c.id,
                    created_at=now_utc - timedelta(days=12),
                )
            )
    await session.flush()

    # 6. User Roadmap & Roadmap Items
    stmt_road = select(Roadmap).where(Roadmap.user_id == user.id)
    res_road = await session.execute(stmt_road)
    roadmap = res_road.scalar_one_or_none()

    if not roadmap:
        roadmap = Roadmap(
            id=uuid4(),
            user_id=user.id,
            career_id=swe_career.id,
            template_version=1,
            title="Software Development Engineer (SDE) Accelerated Roadmap",
            status="active",
            timezone=DEMO_TIMEZONE,
            hours_per_week=20,
            start_date=now_utc - timedelta(days=14),
            target_completion_date=now_utc + timedelta(days=90),
            created_at=now_utc - timedelta(days=14),
            updated_at=now_utc,
        )
        session.add(roadmap)
        await session.flush()

        # Phases
        p1 = RoadmapPhase(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_order=1,
            name="Foundations & Algorithmic Problem Solving",
            description="Core data structures, hash tables, trees, and algorithmic complexity.",
            created_at=now_utc - timedelta(days=14),
        )
        p2 = RoadmapPhase(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_order=2,
            name="Backend Architecture & High-Performance Databases",
            description="Async REST APIs, relational indexing, transaction isolation, and caching.",
            created_at=now_utc - timedelta(days=14),
        )
        p3 = RoadmapPhase(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_order=3,
            name="Distributed Systems & Cloud Infrastructure",
            description="Fault-tolerant messaging queues, worker pools, and gRPC communication.",
            created_at=now_utc - timedelta(days=14),
        )
        for p in [p1, p2, p3]:
            session.add(p)
        await session.flush()

        # Phase 1 Items (all done -> triggers first_phase_done milestone)
        item1 = RoadmapItem(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_id=p1.id,
            item_code="dsa_arrays_hashmap",
            type="problem",
            title="Two Sum & Hash Map Lookup Mastery",
            source_url="https://leetcode.com/problems/two-sum/",
            estimated_minutes=45,
            difficulty=1,
            topic="Arrays",
            skill_id=skills["algorithms"].id,
            status="done",
            completed_at=now_utc - timedelta(days=10),
            order_index=1,
        )
        item2 = RoadmapItem(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_id=p1.id,
            item_code="dsa_linked_lists",
            type="problem",
            title="Fast & Slow Pointer Cycle Detection",
            source_url="https://leetcode.com/problems/linked-list-cycle/",
            estimated_minutes=45,
            difficulty=1,
            topic="Linked Lists",
            skill_id=skills["algorithms"].id,
            status="done",
            completed_at=now_utc - timedelta(days=8),
            order_index=2,
        )
        item3 = RoadmapItem(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_id=p1.id,
            item_code="dsa_trees_dfs",
            type="problem",
            title="Binary Tree Depth-First Search Traversals",
            source_url="https://leetcode.com/problems/binary-tree-inorder-traversal/",
            estimated_minutes=60,
            difficulty=2,
            topic="Trees",
            skill_id=skills["algorithms"].id,
            status="done",
            completed_at=now_utc - timedelta(days=7),
            order_index=3,
        )

        # Phase 2 Items (in progress / done)
        item4 = RoadmapItem(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_id=p2.id,
            item_code="be_fastapi_async",
            type="course",
            title="Async Web Frameworks & Dependency Injection with FastAPI",
            estimated_minutes=120,
            difficulty=2,
            topic="Backend",
            skill_id=skills["fastapi"].id,
            status="done",
            completed_at=now_utc - timedelta(days=4),
            order_index=1,
        )
        item5 = RoadmapItem(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_id=p2.id,
            item_code="be_postgres_indexes",
            type="course",
            title="PostgreSQL Schema Design, Query Plans & B-Tree Indexes",
            estimated_minutes=120,
            difficulty=2,
            topic="Databases",
            skill_id=skills["postgresql"].id,
            status="done",
            completed_at=now_utc - timedelta(days=2),
            order_index=2,
        )
        item6 = RoadmapItem(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_id=p2.id,
            item_code="be_redis_cache",
            type="course",
            title="Redis Cache Invalidation & Sliding-Window Rate Limiting",
            estimated_minutes=90,
            difficulty=2,
            topic="Caching",
            skill_id=skills["fastapi"].id,
            status="in_progress",
            order_index=3,
        )
        item7 = RoadmapItem(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_id=p2.id,
            item_code="be_rest_capstone",
            type="project",
            title="Production REST API Service Capstone",
            estimated_minutes=180,
            difficulty=2,
            topic="Backend",
            skill_id=skills["fastapi"].id,
            status="todo",
            order_index=4,
        )

        # Phase 3 Items (todo)
        item8 = RoadmapItem(
            id=uuid4(),
            roadmap_id=roadmap.id,
            phase_id=p3.id,
            item_code="ds_grpc_comm",
            type="reading",
            title="High-Throughput RPCs with gRPC and Protobuf",
            estimated_minutes=90,
            difficulty=3,
            topic="Microservices",
            skill_id=skills["python"].id,
            status="todo",
            order_index=1,
        )

        for itm in [item1, item2, item3, item4, item5, item6, item7, item8]:
            session.add(itm)
        await session.flush()

        # 7. Planner Tasks linked to roadmap items
        task_past1 = PlannerTask(
            id=uuid4(),
            user_id=user.id,
            roadmap_item_id=item4.id,
            task_type="roadmap_item",
            title=item4.title,
            notes="Completed FastAPI dependency injection exercises with full unit test coverage.",
            estimated_minutes=120,
            scheduled_date=today_local - timedelta(days=4),
            status="completed",
            priority="high",
            completed_at=now_utc - timedelta(days=4),
        )
        task_past2 = PlannerTask(
            id=uuid4(),
            user_id=user.id,
            roadmap_item_id=item5.id,
            task_type="roadmap_item",
            title=item5.title,
            notes="Analyzed EXPLAIN ANALYZE execution trees and created compound b-tree indexes.",
            estimated_minutes=120,
            scheduled_date=today_local - timedelta(days=2),
            status="completed",
            priority="high",
            completed_at=now_utc - timedelta(days=2),
        )
        task_today = PlannerTask(
            id=uuid4(),
            user_id=user.id,
            roadmap_item_id=item6.id,
            task_type="roadmap_item",
            title=item6.title,
            notes="Implement sliding-window token bucket using Redis pipelines.",
            estimated_minutes=90,
            scheduled_date=today_local,
            status="in_progress",
            priority="high",
        )
        task_custom = PlannerTask(
            id=uuid4(),
            user_id=user.id,
            roadmap_item_id=None,
            task_type="user_custom",
            title="Review Raft Consensus Protocol paper",
            notes="Read sections 1-5 of Ongaro & Ousterhout Raft paper for systems interview preparation.",
            estimated_minutes=60,
            scheduled_date=today_local + timedelta(days=1),
            status="pending",
            priority="medium",
        )
        for tsk in [task_past1, task_past2, task_today, task_custom]:
            session.add(tsk)
        await session.flush()

    # 8. Activity Events (Continuous 7-day streak ending today)
    # Check existing activity events for demo user
    stmt_act = select(ActivityEvent).where(ActivityEvent.user_id == user.id)
    res_act = await session.execute(stmt_act)
    existing_events = res_act.scalars().all()

    if not existing_events:
        logger.info("Seeding 7-day continuous activity ledger streak ending today...")
        # Day 6 ago to Day 0 (today)
        activity_plan = [
            (6, "adaptive_test", f"demo_diagnostic_test_{user.id}"),
            (5, "roadmap_item", f"demo_rm_item_1_{user.id}"),
            (4, "roadmap_item", f"demo_rm_item_2_{user.id}"),
            (3, "roadmap_item", f"demo_rm_item_3_{user.id}"),
            (2, "roadmap_item", f"demo_rm_item_4_{user.id}"),
            (1, "interview_session", f"demo_interview_{user.id}"),
            (0, "roadmap_item", f"demo_daily_task_{user.id}"),
        ]

        for days_ago, source_type, source_id in activity_plan:
            event_date = today_local - timedelta(days=days_ago)
            event_time = now_utc - timedelta(days=days_ago)
            ev = ActivityEvent(
                id=uuid4(),
                user_id=user.id,
                source_type=source_type,
                source_id=source_id,
                occurred_at=event_time,
                local_date=event_date,
                tz=DEMO_TIMEZONE,
            )
            session.add(ev)
        await session.flush()

    # 9. Awarded Milestones
    # Ensure all 4 original milestone rules are awarded to demo account
    stmt_rules = select(MilestoneRule).where(MilestoneRule.active.is_(True))
    res_rules = await session.execute(stmt_rules)
    active_rules = res_rules.scalars().all()

    for r in active_rules:
        stmt_m = select(UserMilestone).where(
            UserMilestone.user_id == user.id,
            UserMilestone.rule_id == r.id,
        )
        res_m = await session.execute(stmt_m)
        if not res_m.scalar_one_or_none():
            evidence: Dict[str, Any] = {}
            if r.key == "first_test":
                evidence = {"source_type": "adaptive_test", "count": 1, "score": 92}
            elif r.key == "first_project":
                evidence = {"source_type": "roadmap_item", "count": 1}
            elif r.key == "streak_7_days":
                evidence = {"streak_days": 7, "as_of": str(today_local)}
            elif r.key == "first_phase_done":
                evidence = {"phase_order": 1, "completed_items_count": 3}

            session.add(
                UserMilestone(
                    id=uuid4(),
                    user_id=user.id,
                    rule_id=r.id,
                    awarded_at=now_utc - timedelta(days=1),
                    evidence=evidence,
                )
            )
    await session.flush()

    # 10. Weekly Goals (current week and previous week)
    curr_monday = get_week_monday(today_local)
    prev_monday = curr_monday - timedelta(days=7)

    goals_to_seed = [
        (curr_monday, "roadmap_items", 5),
        (curr_monday, "minutes", 600),
        (prev_monday, "roadmap_items", 4),
        (prev_monday, "minutes", 480),
    ]

    for w_start, g_type, target in goals_to_seed:
        stmt_g = select(WeeklyGoal).where(
            WeeklyGoal.user_id == user.id,
            WeeklyGoal.week_start == w_start,
            WeeklyGoal.goal_type == g_type,
        )
        res_g = await session.execute(stmt_g)
        g = res_g.scalar_one_or_none()
        if not g:
            session.add(
                WeeklyGoal(
                    id=uuid4(),
                    user_id=user.id,
                    week_start=w_start,
                    goal_type=g_type,
                    target=target,
                    created_at=now_utc - timedelta(days=7),
                    updated_at=now_utc,
                )
            )
    await session.flush()

    # 11. Skills & Skill Evidence
    for sk_slug, level, conf, score in [
        ("python", "advanced", "high", 92),
        ("postgresql", "intermediate", "medium", 85),
        ("fastapi", "intermediate", "medium", 88),
        ("algorithms", "advanced", "high", 95),
    ]:
        s = skills[sk_slug]
        stmt_usk = select(UserSkill).where(
            UserSkill.user_id == user.id,
            UserSkill.skill_id == s.id,
        )
        res_usk = await session.execute(stmt_usk)
        usk = res_usk.scalar_one_or_none()
        if usk:
            usk.current_level = level
            usk.confidence = conf
            usk.updated_at = now_utc
        else:
            session.add(
                UserSkill(
                    id=uuid4(),
                    user_id=user.id,
                    skill_id=s.id,
                    current_level=level,
                    confidence=conf,
                    updated_at=now_utc,
                )
            )

        # Skill evidence
        stmt_ev = select(SkillEvidence).where(
            SkillEvidence.user_id == user.id,
            SkillEvidence.skill_id == s.id,
        )
        res_ev = await session.execute(stmt_ev)
        if not res_ev.scalar_one_or_none():
            session.add(
                SkillEvidence(
                    id=uuid4(),
                    user_id=user.id,
                    skill_id=s.id,
                    source_type="test" if sk_slug in ("python", "algorithms") else "roadmap",
                    score=score,
                    level_signal=level,
                    subtopic_scores={"core": score, "advanced": score - 5},
                    summary=f"Demonstrated verified proficiency in {s.name}.",
                    created_at=now_utc - timedelta(days=5),
                )
            )
    await session.flush()

    # 12. User Portfolio
    stmt_port = select(UserPortfolio).where(UserPortfolio.user_id == user.id)
    res_port = await session.execute(stmt_port)
    port = res_port.scalar_one_or_none()

    portfolio_values = {
        "slug": slug.strip().lower(),
        "is_public": True,
        "headline": "Aspiring Software Engineer | Distributed Systems & Backend Enthusiast",
        "about": (
            "Third-year Computer Science student passionate about distributed architectures, "
            "high-throughput backend services, and scalable web platforms. Actively completing "
            "engineering roadmap milestones and shipping real-world open-source tools."
        ),
        "visibility": {
            "about": True,
            "skills": True,
            "projects": True,
            "certificates": True,
            "competitions": True,
            "achievements": True,
        },
        "featured_item_ids": [],
        "custom_projects": [
            {
                "title": "Async Task Distributed Worker",
                "description": "High-performance distributed asynchronous worker engine with sliding-window rate limiting, priority queues, and dead-letter queue resilience built on FastAPI and Redis.",
                "skills": ["Python", "FastAPI", "Redis", "Docker"],
                "link": "https://github.com/alexchen/async-task-worker",
                "completed_date": "2026-09-15",
                "provenance": "self_reported",
            },
            {
                "title": "Interactive Roadmap Navigator",
                "description": "Full-stack career curriculum engine that models skill dependencies as a directed acyclic graph and dynamically computes learning paths based on student study budgets.",
                "skills": ["TypeScript", "React", "PostgreSQL", "SQLAlchemy"],
                "link": "https://github.com/alexchen/roadmap-navigator",
                "completed_date": "2026-10-01",
                "provenance": "roadmap",
            },
        ],
        "custom_certificates": [
            {
                "title": "AWS Certified Cloud Practitioner",
                "issuer": "Amazon Web Services",
                "credential_url": "https://aws.amazon.com/verification",
                "issue_date": "2025-11-15",
                "provenance": "self_reported",
            }
        ],
        "competitions": [
            {
                "title": "National Collegiate Systems Hackathon",
                "award_or_rank": "Top 10 Finalist",
                "description": "Designed and deployed a fault-tolerant microservice cluster handling 10k req/sec under chaos fault injection.",
                "year": 2025,
            }
        ],
        "achievements": [
            {
                "title": "7-Day Consistent Study Streak",
                "description": "Maintained an unbroken 7-day daily activity record completing foundational algorithms and systems coursework.",
                "date": "2026-10-24",
            },
            {
                "title": "Phase 1 Foundations Completed",
                "description": "Successfully completed all Phase 1 Algorithmic & Data Structure problems with full test pass rates.",
                "date": "2026-10-20",
            },
        ],
    }

    if port:
        for k, v in portfolio_values.items():
            setattr(port, k, v)
        port.updated_at = now_utc
    else:
        # Check if slug is used by another user
        stmt_slug = select(UserPortfolio).where(UserPortfolio.slug == portfolio_values["slug"])
        res_slug = await session.execute(stmt_slug)
        existing_slug_owner = res_slug.scalar_one_or_none()
        if existing_slug_owner and existing_slug_owner.user_id != user.id:
            portfolio_values["slug"] = f"{portfolio_values['slug']}-{user.id.hex[:4]}"

        port = UserPortfolio(
            id=uuid4(),
            user_id=user.id,
            **portfolio_values,
            created_at=now_utc - timedelta(days=10),
            updated_at=now_utc,
        )
        session.add(port)
    await session.flush()

    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "name": profile.name,
        "timezone": profile.timezone,
        "assessment_status": attempt.status,
        "holland_code": result_record.holland_code,
        "shortlisted_careers": [c.title for c in [swe_career, ds_career]],
        "roadmap_title": roadmap.title,
        "portfolio_slug": port.slug,
        "portfolio_public": port.is_public,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed realistic demo user account for AI Career Navigator.")
    parser.add_argument("--email", default=DEMO_EMAIL_DEFAULT, help="Demo user email address")
    parser.add_argument("--password", default=DEMO_PASSWORD_DEFAULT, help="Demo user password (min 10 chars)")
    parser.add_argument("--slug", default=DEMO_SLUG_DEFAULT, help="Public portfolio URL slug")
    parser.add_argument("--force-refresh", action="store_true", help="Force wipe and recreate demo user data")
    args = parser.parse_args()

    async def _run() -> None:
        async with async_session_factory() as session:
            try:
                res = await seed_demo_account(
                    session=session,
                    email=args.email,
                    password=args.password,
                    slug=args.slug,
                    force_refresh=args.force_refresh,
                )
                await session.commit()
                print("\n=======================================================")
                print(" DEMO ACCOUNT SEEDED SUCCESSFULLY!")
                print("=======================================================")
                print(f" User ID:            {res['user_id']}")
                print(f" Email:              {res['email']}")
                print(f" Password:           {args.password}")
                print(f" Name:               {res['name']}")
                print(f" Timezone:           {res['timezone']}")
                print(f" Holland Code:       {res['holland_code']}")
                print(f" Shortlisted:        {', '.join(res['shortlisted_careers'])}")
                print(f" Roadmap:            {res['roadmap_title']}")
                print(f" Portfolio URL:      /v1/portfolio/p/{res['portfolio_slug']}")
                print("=======================================================\n")
            except Exception as exc:
                await session.rollback()
                logger.exception("Failed to seed demo account: %s", exc)
                sys.exit(1)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
