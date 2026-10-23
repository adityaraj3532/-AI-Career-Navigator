import argparse
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.models.career import Career

logger = logging.getLogger("scripts.verify_career")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def verify_career(
    reviewer: str,
    career_code: str | None = None,
    career_id: str | None = None,
    verify_all: bool = False,
) -> int:
    if not any([career_code, career_id, verify_all]):
        raise ValueError("Must specify --code, --id, or --all")

    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        if verify_all:
            stmt = (
                update(Career)
                .where(Career.status == "draft")
                .values(
                    status="verified",
                    reviewer=reviewer,
                    verified_at=now,
                )
            )
            res = await session.execute(stmt)
            await session.commit()
            count = res.rowcount
            logger.info("Verified all draft careers (%d records) by reviewer '%s'", count, reviewer)
            return count

        if career_code:
            query = select(Career).where(Career.code == career_code)
        else:
            c_uuid = uuid.UUID(career_id)
            query = select(Career).where(Career.id == c_uuid)

        res = await session.execute(query)
        career = res.scalar_one_or_none()

        if not career:
            logger.error("Career not found for code=%s, id=%s", career_code, career_id)
            return 0

        career.status = "verified"
        career.reviewer = reviewer
        career.verified_at = now
        await session.commit()
        logger.info("Career '%s' (%s) verified by '%s'", career.title, career.code, reviewer)
        return 1


def parse_args():
    parser = argparse.ArgumentParser(description="Mark career(s) as verified")
    parser.add_argument("--reviewer", required=True, help="Reviewer name or identifier")
    parser.add_argument("--code", help="Career code to verify")
    parser.add_argument("--id", help="Career UUID to verify")
    parser.add_argument("--all", action="store_true", help="Verify all draft careers")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        verify_career(
            reviewer=args.reviewer,
            career_code=args.code,
            career_id=args.id,
            verify_all=args.all,
        )
    )
