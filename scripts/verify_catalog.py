import argparse
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Type
from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.models.career import (
    Career,
    Certificate,
    College,
    Course,
    Exam,
    Internship,
)

logger = logging.getLogger("scripts.verify_catalog")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ENTITY_MAP = {
    "career": Career,
    "exam": Exam,
    "college": College,
    "course": Course,
    "certificate": Certificate,
    "internship": Internship,
}


async def verify_entities(
    entity_type: str,
    reviewer: str,
    code: str | None = None,
    entity_id: str | None = None,
    verify_all: bool = False,
) -> int:
    now = datetime.now(timezone.utc)
    target_models: List[Type] = []

    if entity_type == "all":
        target_models = list(ENTITY_MAP.values())
    elif entity_type in ENTITY_MAP:
        target_models = [ENTITY_MAP[entity_type]]
    else:
        raise ValueError(f"Unknown entity type: {entity_type}. Must be one of {list(ENTITY_MAP.keys())} or 'all'")

    total_verified = 0

    async with async_session_factory() as session:
        for model in target_models:
            if verify_all:
                stmt = (
                    update(model)
                    .where(model.status == "draft")
                    .values(
                        status="verified",
                        reviewer=reviewer,
                        last_verified_at=now,
                    )
                )
                res = await session.execute(stmt)
                count = res.rowcount
                total_verified += count
                logger.info("Verified all draft records in %s (%d records) by '%s'", model.__tablename__, count, reviewer)
            else:
                if not code and not entity_id:
                    raise ValueError("Must specify --code, --id, or --all")

                if code and hasattr(model, "code"):
                    q = select(model).where(model.code == code)
                elif code and hasattr(model, "name"):
                    q = select(model).where(model.name == code)
                elif entity_id:
                    q = select(model).where(model.id == uuid.UUID(entity_id))
                else:
                    continue

                res = await session.execute(q)
                record = res.scalar_one_or_none()
                if record:
                    record.status = "verified"
                    record.reviewer = reviewer
                    record.last_verified_at = now
                    if hasattr(record, "verified_at"):
                        record.verified_at = now
                    total_verified += 1
                    logger.info("Record %s (%s) verified by '%s'", getattr(record, "title", getattr(record, "name", str(record.id))), model.__tablename__, reviewer)

        await session.commit()

    return total_verified


def parse_args():
    parser = argparse.ArgumentParser(description="Verify catalog entities (Career, Exam, College, Course, Certificate, Internship)")
    parser.add_argument("--entity", default="career", choices=["career", "exam", "college", "course", "certificate", "internship", "all"], help="Target entity type")
    parser.add_argument("--reviewer", required=True, help="Reviewer name or email identifier")
    parser.add_argument("--code", help="Entity unique code or name to verify")
    parser.add_argument("--id", help="Entity UUID to verify")
    parser.add_argument("--all", action="store_true", help="Verify all draft records")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        verify_entities(
            entity_type=args.entity,
            reviewer=args.reviewer,
            code=args.code,
            entity_id=args.id,
            verify_all=args.all,
        )
    )
