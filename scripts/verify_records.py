"""Independent Human Verification CLI.

Enforces:
1. Requires a verified, non-generic human reviewer name (refuses 'system', 'script', 'admin', etc.).
2. Takes record IDs/codes from an external input file provided by a human reviewer.
3. Sets status='verified', recording reviewer name and precise UTC verification timestamp.
4. Provides --dry-run capability to inspect matched entities before committing.

Usage:
    python -m scripts.verify_records --reviewer "Dr. Jane Doe" --file verified_ids.txt [--entity-type auto] [--dry-run]
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.adaptive_test import TestQuestionBank
from app.models.career import Career, Certificate, College, Course, Exam, Internship
from app.models.exam_cycle import ExamCycle
from app.models.interview import InterviewQuestion
from app.models.roadmap import RoadmapTemplate, TemplateItem

PROHIBITED_REVIEWER_NAMES: Set[str] = {
    "system",
    "script",
    "admin",
    "system_verifier",
    "bot",
    "auto",
    "automated",
    "test",
    "seed",
    "ai",
    "crawler",
    "anonymous",
    "root",
    "default",
    "reviewer",
    "user",
    "null",
    "none",
    "unknown",
}


def validate_reviewer_name(name: Optional[str]) -> str:
    """Validate that the reviewer name is non-empty, non-generic, and human."""
    if not name or not name.strip():
        raise ValueError("Reviewer name is required and cannot be empty.")

    clean = name.strip()
    lowered = clean.lower()

    if len(clean) < 3:
        raise ValueError(f"Reviewer name '{clean}' is too short (minimum 3 characters).")

    # Exact or component match check against prohibited generic names
    words = set(lowered.replace("_", " ").replace("-", " ").split())
    if lowered in PROHIBITED_REVIEWER_NAMES or words.intersection(PROHIBITED_REVIEWER_NAMES):
        raise ValueError(
            f"Reviewer name '{clean}' is a generic, automated, or prohibited role name. "
            f"Official verification requires an authenticated human reviewer's full name (e.g. 'Dr. Priya Sharma')."
        )

    return clean


def parse_id_file(file_path: Path) -> List[str]:
    """Parse list of IDs or codes from plain text or JSON file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Verification ID file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    # Check if JSON
    if content.startswith("["):
        try:
            data = json.loads(content)
            return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            pass

    # Plain text: line by line, skip comments starting with '#'
    ids = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.append(line)
    return ids


ENTITY_MODELS = [
    {
        "type": "career",
        "model": Career,
        "id_col": "id",
        "code_col": "code",
        "title_col": "title",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": "verified_at",
    },
    {
        "type": "college",
        "model": College,
        "id_col": "id",
        "code_col": "name",
        "title_col": "name",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "exam",
        "model": Exam,
        "id_col": "id",
        "code_col": "code",
        "title_col": "name",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "course",
        "model": Course,
        "id_col": "id",
        "code_col": "code",
        "title_col": "title",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "certificate",
        "model": Certificate,
        "id_col": "id",
        "code_col": "code",
        "title_col": "name",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "internship",
        "model": Internship,
        "id_col": "id",
        "code_col": "code",
        "title_col": "title",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "exam_cycle",
        "model": ExamCycle,
        "id_col": "id",
        "code_col": "cycle_name",
        "title_col": "cycle_name",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "test_question",
        "model": TestQuestionBank,
        "id_col": "id",
        "code_col": None,
        "title_col": "topic",
        "reviewer_attr": "reviewer",
        "date_attr": "verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "interview_question",
        "model": InterviewQuestion,
        "id_col": "id",
        "code_col": None,
        "title_col": "text",
        "reviewer_attr": "last_verified_by",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "template_item",
        "model": TemplateItem,
        "id_col": "id",
        "code_col": "item_code",
        "title_col": "title",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
    {
        "type": "roadmap_template",
        "model": RoadmapTemplate,
        "id_col": "id",
        "code_col": None,
        "title_col": "title",
        "reviewer_attr": "reviewer",
        "date_attr": "last_verified_at",
        "extra_date_attr": None,
    },
]


async def verify_records_from_ids(
    session: AsyncSession,
    reviewer: str,
    id_list: List[str],
    entity_type: Optional[str] = None,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    verified_results = []

    configs = ENTITY_MODELS
    if entity_type and entity_type != "auto":
        configs = [c for c in ENTITY_MODELS if c["type"] == entity_type]
        if not configs:
            raise ValueError(f"Unknown entity type: '{entity_type}'. Allowed: {[c['type'] for c in ENTITY_MODELS]}")

    for raw_id in id_list:
        matched = False
        parsed_uuid = None
        try:
            parsed_uuid = UUID(raw_id)
        except ValueError:
            parsed_uuid = None

        for cfg in configs:
            model = cfg["model"]
            stmt = select(model)
            if parsed_uuid:
                stmt = stmt.where(model.id == parsed_uuid)
            elif cfg["code_col"]:
                col = getattr(model, cfg["code_col"])
                stmt = stmt.where(col == raw_id)
            else:
                continue

            res = await session.execute(stmt)
            obj = res.scalar_one_or_none()
            if obj:
                matched = True
                setattr(obj, "status", "verified")
                setattr(obj, cfg["reviewer_attr"], reviewer)
                setattr(obj, cfg["date_attr"], now)
                if cfg["extra_date_attr"]:
                    setattr(obj, cfg["extra_date_attr"], now)

                title_val = getattr(obj, cfg["title_col"], str(obj.id))
                if isinstance(title_val, str) and len(title_val) > 40:
                    title_val = title_val[:37] + "..."

                verified_results.append({
                    "type": cfg["type"],
                    "id": str(obj.id),
                    "identifier": raw_id,
                    "title": title_val,
                    "reviewer": reviewer,
                    "verified_at": now.isoformat(),
                })
                break

        if not matched:
            print(f"[WARNING] Record identifier '{raw_id}' was not found in target tables.")

    if not dry_run:
        await session.commit()
    else:
        await session.rollback()

    return verified_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Official Human Verification CLI")
    parser.add_argument("--reviewer", required=True, help="Full human name of the official reviewer")
    parser.add_argument("--file", required=True, type=Path, help="Path to file containing record IDs or codes to verify")
    parser.add_argument("--entity-type", default="auto", help="Optional specific entity type to verify, or 'auto'")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without committing changes")

    args = parser.parse_args()

    # 1. Enforce strict human reviewer validation
    reviewer = validate_reviewer_name(args.reviewer)

    # 2. Parse ID file
    id_list = parse_id_file(args.file)
    if not id_list:
        print(f"No valid record IDs found in {args.file}")
        sys.exit(0)

    mode_label = "[DRY-RUN]" if args.dry_run else "[LIVE]"
    print(f"\n=======================================================")
    print(f" {mode_label} OFFICIAL RECORD VERIFICATION")
    print(f" Reviewer: {reviewer}")
    print(f" Input File: {args.file} ({len(id_list)} identifiers)")
    print(f"=======================================================\n")

    async def _run():
        async with async_session_factory() as session:
            results = await verify_records_from_ids(
                session=session,
                reviewer=reviewer,
                id_list=id_list,
                entity_type=args.entity_type,
                dry_run=args.dry_run,
            )

        print(f"\nVerification Results ({len(results)} matched):")
        print(f"{'Type':<18} {'ID':<38} {'Title / Identifier':<30} {'Status'}")
        print("-" * 95)
        for r in results:
            status_label = "VERIFIED (DRY-RUN)" if args.dry_run else "VERIFIED"
            print(f"{r['type']:<18} {r['id']:<38} {r['title']:<30} {status_label}")
        print("=======================================================\n")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
