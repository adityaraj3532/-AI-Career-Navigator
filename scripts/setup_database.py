"""Master Database Setup and Verification Orchestrator.

Executes complete, idempotent platform database initialization:
1. Verifies PostgreSQL and Redis health checks
2. Runs Alembic migrations up to head (015_create_ai_chat)
3. Seeds RIASEC assessment versions and questions (app/data/seed/assessment_questions.json)
4. Seeds master skills catalog (app/data/seed/skills_catalog.json)
5. Seeds comprehensive career catalog (careers, exams, colleges, courses, certificates, internships)
6. Seeds exam cycles (app/data/seed/exam_cycles.json)
7. Seeds adaptive test question bank (app/data/seed/test_questions.json)
8. Seeds roadmap templates, phases, and items (app/data/seed/roadmap_templates.json)
9. Seeds interview questions (app/data/seed/interview_questions.json)
10. Seeds milestone rules (app/data/seed/milestone_rules.json)
11. Verifies and activates catalog entities, questions, and roadmaps
12. Seeds admin account (admin@career-navigator.io)
13. Seeds full-spectrum demo student account (demo@career-navigator.io / "Alex Chen")
14. Validates table row counts and outputs setup report

Usage:
    python -m scripts.setup_database [--skip-migrations] [--force-refresh-demo]
"""

import argparse
import asyncio
import logging
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from typing import Dict

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, check_db_health
from app.core.redis import check_redis_health, close_redis
from app.core.security import hash_password
from app.models.user import User
from app.services.activity_service import seed_milestones
from scripts.seed_assessment import seed_assessment_data
from scripts.seed_career_catalog import seed_career_catalog
from scripts.seed_demo_account import seed_demo_account
from scripts.seed_exam_cycles import seed_exam_cycles
from scripts.seed_interview_questions import seed_interview_questions
from scripts.seed_roadmaps import seed_roadmaps
from scripts.seed_skills_catalog import seed_skills
from scripts.seed_test_questions import seed_test_questions
from scripts.verify_catalog import verify_entities
from scripts.verify_interview_question import verify_interview_questions
from scripts.verify_question import verify_questions
from scripts.verify_roadmap_item import verify_items

logger = logging.getLogger("scripts.setup_database")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR / "app" / "data" / "seed"
ALEMBIC_INI = BASE_DIR / "alembic.ini"


def run_alembic_migrations() -> None:
    """Run Alembic migrations to the latest revision."""
    logger.info("Applying Alembic migrations up to head...")
    alembic_cfg = Config(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations successfully applied.")


async def ensure_admin_account(session: AsyncSession, email: str, password: str) -> User:
    """Ensure an active admin account exists idempotently."""
    clean_email = email.strip().lower()
    stmt = select(User).where(User.email == clean_email)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if user:
        user.hashed_password = hash_password(password)
        user.role = "admin"
        user.is_active = True
        logger.info("Admin account '%s' already exists. Updated credentials.", clean_email)
    else:
        user = User(
            email=clean_email,
            hashed_password=hash_password(password),
            role="admin",
            education_level="college",
            is_active=True,
        )
        session.add(user)
        logger.info("Created new admin account '%s'.", clean_email)

    await session.commit()
    return user


async def generate_table_report(session: AsyncSession) -> Dict[str, int]:
    """Inspect and report row counts for all public tables."""
    res = await session.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """))
    tables = [r[0] for r in res.fetchall()]
    report: Dict[str, int] = {}
    for t in tables:
        try:
            cnt = (await session.execute(text(f'SELECT count(*) FROM "{t}"'))).scalar()
            report[t] = cnt or 0
        except Exception:
            report[t] = -1
    return report


async def setup_database(force_refresh_demo: bool = True) -> None:
    """Master entrypoint executing full database setup."""
    print("\n=======================================================")
    print(" AI CAREER NAVIGATOR – FULL DATABASE INITIALIZATION")
    print("=======================================================\n")

    # 1. Health checks
    logger.info("Checking PostgreSQL and Redis health...")
    db_ok = await check_db_health()
    if not db_ok:
        logger.error("PostgreSQL is unreachable! Please ensure PostgreSQL is running.")
        sys.exit(1)
    logger.info("PostgreSQL health check: OK")

    redis_ok = await check_redis_health()
    logger.info("Redis health check: %s", "OK" if redis_ok else "DEGRADED (Continuing without Redis cache)")

    # 3. Seed Master Catalogs
    async with async_session_factory() as session:
        # A. Assessment Questions
        p_assess = SEED_DIR / "assessment_questions.json"
        if p_assess.is_file():
            ver = await seed_assessment_data(session, p_assess)
            await session.commit()
            logger.info("Seeded assessment version %d: '%s'", ver.version_number, ver.title)

        # B. Skills Catalog
        p_skills = SEED_DIR / "skills_catalog.json"
        if p_skills.is_file():
            sk_count = await seed_skills(session, p_skills)
            logger.info("Seeded %d skills from %s", sk_count, p_skills.name)

        # C. Career Catalog
        p_cat = SEED_DIR / "career_catalog.json"
        if p_cat.is_file():
            cat_counts = await seed_career_catalog(session, p_cat)
            logger.info("Seeded catalog items from %s: %s", p_cat.name, cat_counts)

        # D. Exam Cycles
        p_cycles = SEED_DIR / "exam_cycles.json"
        if p_cycles.is_file():
            cyc_count = await seed_exam_cycles(session, p_cycles)
            logger.info("Seeded %d exam cycles from %s", cyc_count, p_cycles.name)

        # E. Adaptive Test Questions
        p_test_q = SEED_DIR / "test_questions.json"
        if p_test_q.is_file():
            tq_count = await seed_test_questions(session, p_test_q)
            logger.info("Seeded %d adaptive test questions from %s", tq_count, p_test_q.name)

        # F. Roadmaps
        p_roadmaps = SEED_DIR / "roadmap_templates.json"
        if p_roadmaps.is_file():
            rm_count = await seed_roadmaps(session, p_roadmaps)
            logger.info("Seeded %d roadmap templates from %s", rm_count, p_roadmaps.name)

        # G. Interview Questions
        p_iq = SEED_DIR / "interview_questions.json"
        if p_iq.is_file():
            iq_count = await seed_interview_questions(session, p_iq)
            logger.info("Seeded %d interview questions from %s", iq_count, p_iq.name)

        # H. Milestone Rules
        m_rules = await seed_milestones(session)
        await session.commit()
        logger.info("Seeded %d milestone rules", len(m_rules))

        # 4. Verify & Publish Master Data
        logger.info("Verifying catalog entities, questions, and roadmaps...")
        reviewer = "system_verifier"
        await verify_entities(entity_type="all", reviewer=reviewer, verify_all=True)
        await verify_questions(session, verify_all=True, reviewer=reviewer)
        await verify_interview_questions(session, reviewer=reviewer, all_questions=True)
        await verify_items(session, reviewer=reviewer, all_items=True)
        logger.info("Master data verification complete.")

        # 5. Admin Account
        admin = await ensure_admin_account(
            session=session,
            email="admin@career-navigator.io",
            password="AdminAccount@2026!",
        )

        # 6. Comprehensive Demo Student Account
        logger.info("Seeding realistic demo student account (Alex Chen)...")
        demo_res = await seed_demo_account(
            session=session,
            email="demo@career-navigator.io",
            password="DemoAccount@2026!",
            slug="alex-chen",
            force_refresh=force_refresh_demo,
        )
        await session.commit()
        logger.info("Demo account seeded: %s (%s)", demo_res["email"], demo_res["user_id"])

        # 7. Final Table Report
        report = await generate_table_report(session)

    await close_redis()

    print("\n=======================================================")
    print(" DATABASE SETUP AND VERIFICATION COMPLETE!")
    print("=======================================================")
    print(f" Admin Account:      {admin.email} / AdminAccount@2026!")
    print(f" Demo Student:       {demo_res['email']} / DemoAccount@2026!")
    print(f" Demo Profile:       {demo_res['name']} ({demo_res['timezone']})")
    print(f" Holland Assessment: Code {demo_res['holland_code']} (Status: {demo_res['assessment_status']})")
    print(f" Shortlist:          {', '.join(demo_res['shortlisted_careers'])}")
    print(f" Roadmap:            {demo_res['roadmap_title']}")
    print(f" Public Portfolio:   /v1/portfolio/p/{demo_res['portfolio_slug']}")
    print("-------------------------------------------------------")
    print(" Database Table Statistics:")
    for tbl, count in sorted(report.items()):
        if count > 0:
            print(f"   * {tbl:<36} {count:>6} rows")
    print("=======================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Career Navigator Database Setup and Verification Orchestrator.")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip running Alembic migrations")
    parser.add_argument("--no-force-demo", action="store_true", help="Do not wipe demo account if already exists")
    args = parser.parse_args()

    if not args.skip_migrations:
        run_alembic_migrations()

    asyncio.run(setup_database(
        force_refresh_demo=not args.no_force_demo,
    ))


if __name__ == "__main__":
    main()
