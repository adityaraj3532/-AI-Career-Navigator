"""Revert catalog and question items to draft and clear verification metadata.

Supports dry-run mode and live execution.
Tables affected:
- careers
- colleges
- exams
- courses
- certificates
- internships
- exam_cycles
- test_question_banks
- interview_questions
- template_items
- roadmap_templates

Usage:
    python -m scripts.revert_to_draft [--dry-run]
"""
import argparse
import asyncio
from pathlib import Path
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.database import async_session_factory

TABLE_CONFIGS = [
    {
        "table": "careers",
        "update_sql": """
            UPDATE careers
            SET status = 'draft', reviewer = NULL, verified_at = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR verified_at IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
    {
        "table": "colleges",
        "update_sql": """
            UPDATE colleges
            SET status = 'draft', reviewer = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
    {
        "table": "exams",
        "update_sql": """
            UPDATE exams
            SET status = 'draft', reviewer = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
    {
        "table": "courses",
        "update_sql": """
            UPDATE courses
            SET status = 'draft', reviewer = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
    {
        "table": "certificates",
        "update_sql": """
            UPDATE certificates
            SET status = 'draft', reviewer = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
    {
        "table": "internships",
        "update_sql": """
            UPDATE internships
            SET status = 'draft', reviewer = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
    {
        "table": "exam_cycles",
        "update_sql": """
            UPDATE exam_cycles
            SET status = 'draft', reviewer = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
    {
        "table": "test_question_banks",
        "update_sql": """
            UPDATE test_question_banks
            SET status = 'draft', reviewer = NULL, verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "verified_at",
    },
    {
        "table": "interview_questions",
        "update_sql": """
            UPDATE interview_questions
            SET status = 'draft', last_verified_by = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR last_verified_by IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "last_verified_by",
        "date_col": "last_verified_at",
    },
    {
        "table": "template_items",
        "update_sql": """
            UPDATE template_items
            SET status = 'draft', reviewer = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
    {
        "table": "roadmap_templates",
        "update_sql": """
            UPDATE roadmap_templates
            SET status = 'draft', reviewer = NULL, last_verified_at = NULL
            WHERE status <> 'draft' OR reviewer IS NOT NULL OR last_verified_at IS NOT NULL
        """,
        "reviewer_col": "reviewer",
        "date_col": "last_verified_at",
    },
]


async def get_table_counts(session) -> Dict[str, Dict[str, int]]:
    counts = {}
    for cfg in TABLE_CONFIGS:
        t = cfg["table"]
        res = await session.execute(text(f"SELECT status, count(*) FROM {t} GROUP BY status"))
        counts[t] = dict(res.fetchall())
    return counts


async def run_revert(dry_run: bool = False) -> None:
    mode_str = "[DRY-RUN]" if dry_run else "[LIVE]"
    print(f"\n=======================================================")
    print(f" {mode_str} REVERT CATALOG & QUESTIONS TO DRAFT")
    print(f"=======================================================\n")

    async with async_session_factory() as session:
        before_counts = await get_table_counts(session)

        print("BEFORE COUNTS BY STATUS:")
        print(f"{'Table':<25} {'Draft':<10} {'Verified':<10} {'Other':<10}")
        print("-" * 55)
        for tbl, st in before_counts.items():
            draft_c = st.get("draft", 0)
            ver_c = st.get("verified", 0)
            other_c = sum(v for k, v in st.items() if k not in ("draft", "verified"))
            print(f"{tbl:<25} {draft_c:<10} {ver_c:<10} {other_c:<10}")

        total_affected = 0
        for cfg in TABLE_CONFIGS:
            res = await session.execute(text(cfg["update_sql"]))
            total_affected += res.rowcount

        if dry_run:
            await session.rollback()
            print("\n-------------------------------------------------------")
            print(f"DRY RUN COMPLETE: {total_affected} rows would be updated to draft.")
            print("Changes were rolled back.")
            return

        await session.commit()

        after_counts = await get_table_counts(session)

        print("\n-------------------------------------------------------")
        print(f"LIVE EXECUTION COMPLETE: {total_affected} rows reverted to draft.")
        print("-------------------------------------------------------\n")
        print("AFTER COUNTS BY STATUS:")
        print(f"{'Table':<25} {'Draft':<10} {'Verified':<10} {'Other':<10}")
        print("-" * 55)
        for tbl, st in after_counts.items():
            draft_c = st.get("draft", 0)
            ver_c = st.get("verified", 0)
            other_c = sum(v for k, v in st.items() if k not in ("draft", "verified"))
            print(f"{tbl:<25} {draft_c:<10} {ver_c:<10} {other_c:<10}")
        print("=======================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Revert catalog records and questions to draft")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without committing")
    args = parser.parse_args()

    asyncio.run(run_revert(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
