"""Master Database Setup and Seeding Orchestrator.

Executes complete, idempotent platform database initialization:
1. Verifies PostgreSQL and Redis health checks
2. Runs Alembic migrations up to head
3. Seeds RIASEC assessment versions and questions (app/data/seed/assessment_questions.json)
4. Seeds master skills catalog (app/data/seed/skills_catalog.json)
5. Seeds comprehensive career catalog (careers, exams, colleges, courses, certificates, internships)
6. Seeds exam cycles (app/data/seed/exam_cycles.json)
7. Seeds adaptive test question bank (app/data/seed/test_questions.json)
8. Seeds roadmap templates, phases, and items (app/data/seed/roadmap_templates.json)
9. Seeds interview questions (app/data/seed/interview_questions.json)
10. Seeds milestone rules (app/data/seed/milestone_rules.json)
11. Seeds realistic demo student account (demo@example.com / "Alex Chen")
12. Validates table row counts and outputs setup report

INVARIANT: All catalog items, test questions, and interview questions remain in status='draft'.
No records are ever automatically marked verified during seeding.

Usage:
    python -m scripts.setup_database [--skip-migrations] [--force-refresh-demo]
"""

import argparse
import asyncio
import logging
from pathlib import Path
import sys
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, check_db_health
from app.core.redis import check_redis_health, close_redis
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


async def generate_table_report(session: AsyncSession) -> Dict[str, int]:
    """Inspect and report row counts for all public tables."""
    res = await session.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """))
    tables = [row[0] for row in res.fetchall()]
    report = {}
    for tbl in tables:
        count_res = await session.execute(text(f"SELECT COUNT(*) FROM {tbl};"))
        report[tbl] = count_res.scalar() or 0
    return report


async def setup_database(force_refresh_demo: bool = False) -> None:
    print("\n=======================================================")
    print(" AI CAREER NAVIGATOR — DATABASE INITIALIZATION")
    print("=======================================================\n")

    # 1. Connectivity Pre-checks
    db_ok = await check_db_health()
    if not db_ok:
        logger.error("Database health check failed. Ensure PostgreSQL is running.")
        sys.exit(1)
    logger.info("PostgreSQL database connection verified.")

    redis_ok = await check_redis_health()
    if not redis_ok:
        logger.warning("Redis health check failed. System will operate in memory-fallback mode.")
    else:
        logger.info("Redis cache and rate limiter verified.")

    # 2. Seed Master Catalogs and Domain Data (All seeded as status='draft')
    async with async_session_factory() as session:
        # A. RIASEC Assessment Questions
        p_assess = SEED_DIR / "assessment_questions.json"
        if p_assess.is_file():
            assess_count = await seed_assessment_data(session, p_assess)
            logger.info("Seeded %d RIASEC questions from %s", assess_count, p_assess.name)

        # B. Skills Catalog
        p_skills = SEED_DIR / "skills_catalog.json"
        if p_skills.is_file():
            skills_count = await seed_skills(session, p_skills)
            logger.info("Seeded %d skills from %s", skills_count, p_skills.name)

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

        # 4. Comprehensive Demo Student Account (demo@example.com)
        logger.info("Seeding realistic demo student account (Alex Chen)...")
        demo_res = await seed_demo_account(
            session=session,
            email="demo@example.com",
            slug="alex-chen",
            force_refresh=force_refresh_demo,
        )
        await session.commit()
        logger.info("Demo account seeded: %s (%s)", demo_res["email"], demo_res["user_id"])

        # 5. Final Table Report
        report = await generate_table_report(session)

    await close_redis()

    print("\n=======================================================")
    print(" DATABASE SEEDING COMPLETE (ALL ITEMS IN DRAFT STATUS)")
    print("=======================================================")
    print(f" Demo Student:       {demo_res['email']}")
    print(f" Demo Password:      {demo_res['password']}")
    print(f" Demo Profile:       {demo_res['name']} ({demo_res['timezone']})")
    print(f" Holland Assessment: Code {demo_res['holland_code']} (Status: {demo_res['assessment_status']})")
    print(f" Shortlist:          {', '.join(demo_res['shortlisted_careers'])}")
    print(f" Roadmap:            {demo_res['roadmap_title']}")
    print(f" Public Portfolio:   /v1/portfolio/p/{demo_res['portfolio_slug']}")
    print("-------------------------------------------------------")
    print(" Note: Admin creation is separated. Run: python -m scripts.create_admin")
    print(" Note: Verification is separated. Run: python -m scripts.verify_records")
    print("-------------------------------------------------------")
    print(" Database Table Statistics:")
    for tbl, count in sorted(report.items()):
        if count > 0:
            print(f"   * {tbl:<40} {count:>4} rows")
    print("=======================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Master Database Setup and Verification Orchestrator")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip running Alembic migrations")
    parser.add_argument("--force-refresh-demo", action="store_true", help="Wipe and regenerate demo student account")
    args = parser.parse_args()

    # 1. Run migrations synchronously before starting the asyncio event loop
    if not args.skip_migrations:
        run_alembic_migrations()

    asyncio.run(setup_database(
        force_refresh_demo=args.force_refresh_demo,
    ))


if __name__ == "__main__":
    main()
