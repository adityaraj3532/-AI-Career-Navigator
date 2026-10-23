import asyncio
import json
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.career import Career

logger = logging.getLogger("scripts.seed_careers")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def seed_careers_data(session: AsyncSession, json_path: Path) -> int:
    if not json_path.is_file():
        raise FileNotFoundError(f"Seed file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        careers_data = json.load(f)

    inserted = 0
    updated = 0

    for item in careers_data:
        code = item["code"]
        stmt = select(Career).where(Career.code == code)
        res = await session.execute(stmt)
        career = res.scalar_one_or_none()

        if career:
            career.title = item["title"]
            career.cluster = item["cluster"]
            career.overview = item["overview"]
            career.source_url = item["source_url"]
            career.dimension_weights = item["dimension_weights"]
            # Keep existing status and verification info if already verified
            updated += 1
        else:
            career = Career(
                code=code,
                title=item["title"],
                cluster=item["cluster"],
                overview=item["overview"],
                status=item.get("status", "draft"),
                source_url=item["source_url"],
                dimension_weights=item["dimension_weights"],
            )
            session.add(career)
            inserted += 1

    await session.commit()
    logger.info("Career seeding complete! Inserted: %d, Updated: %d, Total: %d", inserted, updated, len(careers_data))
    return inserted + updated


async def main() -> None:
    seed_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "careers.json"
    async with async_session_factory() as session:
        await seed_careers_data(session, seed_file)


if __name__ == "__main__":
    asyncio.run(main())
