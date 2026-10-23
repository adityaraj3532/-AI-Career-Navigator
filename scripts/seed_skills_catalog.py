import asyncio
import json
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.skill import Skill


async def seed_skills(session: AsyncSession, json_path: Path) -> int:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    skills_data = data.get("skills", [])
    seeded_count = 0

    for item in skills_data:
        skill_id = UUID(item["id"])
        stmt = select(Skill).where(Skill.id == skill_id)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.slug = item["slug"]
            existing.name = item["name"]
            existing.description = item.get("description")
            existing.aliases = item.get("aliases", [])
            existing.category = item.get("category", "General")
        else:
            new_skill = Skill(
                id=skill_id,
                slug=item["slug"],
                name=item["name"],
                description=item.get("description"),
                aliases=item.get("aliases", []),
                category=item.get("category", "General"),
            )
            session.add(new_skill)
        seeded_count += 1

    await session.commit()
    return seeded_count


async def main():
    json_path = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "skills_catalog.json"
    async with async_session_factory() as session:
        count = await seed_skills(session, json_path)
        print(f"Successfully seeded/updated {count} skills from {json_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
