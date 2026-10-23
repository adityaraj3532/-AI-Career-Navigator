import asyncio
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.career import Career
from app.models.roadmap import RoadmapTemplate, TemplateItem, TemplatePhase
from app.models.skill import Skill
from app.services.roadmap_engine import validate_prerequisite_graph


async def seed_roadmaps(session: AsyncSession, json_path: Path) -> int:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    templates_data = data.get("templates", [])
    seeded_count = 0

    for t_data in templates_data:
        career_code = t_data["career_code"]
        c_stmt = select(Career).where(Career.code == career_code)
        c_res = await session.execute(c_stmt)
        career = c_res.scalar_one_or_none()
        if not career:
            print(f"Skipping roadmap template for career '{career_code}' - career not found.")
            continue

        items_data = t_data.get("items", [])
        # 1. Validate prerequisite graph on load: no cycles, no missing references
        validate_prerequisite_graph(items_data)

        # 2. Upsert RoadmapTemplate
        tmpl_stmt = select(RoadmapTemplate).where(
            RoadmapTemplate.career_id == career.id,
            RoadmapTemplate.version == t_data["version"],
        )
        t_res = await session.execute(tmpl_stmt)
        template = t_res.scalar_one_or_none()

        if template:
            template.title = t_data["title"]
            template.description = t_data.get("description")
            if template.status != "verified":
                template.status = t_data.get("status", "draft")
        else:
            template = RoadmapTemplate(
                career_id=career.id,
                version=t_data["version"],
                title=t_data["title"],
                description=t_data.get("description"),
                status=t_data.get("status", "draft"),
            )
            session.add(template)
            await session.flush()

        # 3. Upsert Phases
        phase_map = {}
        for p_data in t_data.get("phases", []):
            order = p_data["phase_order"]
            p_stmt = select(TemplatePhase).where(
                TemplatePhase.template_id == template.id,
                TemplatePhase.phase_order == order,
            )
            pres = await session.execute(p_stmt)
            phase = pres.scalar_one_or_none()
            if phase:
                phase.name = p_data["name"]
                phase.description = p_data.get("description")
            else:
                phase = TemplatePhase(
                    template_id=template.id,
                    name=p_data["name"],
                    phase_order=order,
                    description=p_data.get("description"),
                )
                session.add(phase)
                await session.flush()
            phase_map[order] = phase.id

        # 4. Upsert Items
        for it in items_data:
            item_code = it["item_code"]
            it_stmt = select(TemplateItem).where(
                TemplateItem.template_id == template.id,
                TemplateItem.item_code == item_code,
            )
            ires = await session.execute(it_stmt)
            item = ires.scalar_one_or_none()

            skill_id = None
            if it.get("skill_slug"):
                sk_stmt = select(Skill).where(Skill.slug == it["skill_slug"])
                sk_res = await session.execute(sk_stmt)
                sk = sk_res.scalar_one_or_none()
                if sk:
                    skill_id = sk.id

            phase_id = phase_map.get(it.get("phase_order"))

            if item:
                item.phase_id = phase_id
                item.type = it["type"]
                item.title = it["title"]
                item.source_url = it.get("source_url")
                item.estimated_minutes = it.get("estimated_minutes", 60)
                item.difficulty = it.get("difficulty", 1)
                item.topic = it["topic"]
                item.skill_id = skill_id
                item.prerequisites = it.get("prerequisites", [])
                item.optional = it.get("optional", False)
                item.sequence_order = it.get("sequence_order", 0)
                item.extra_data = it.get("extra_data", {})
                if item.status != "verified":
                    item.status = it.get("status", "draft")
            else:
                item = TemplateItem(
                    template_id=template.id,
                    phase_id=phase_id,
                    item_code=item_code,
                    type=it["type"],
                    title=it["title"],
                    source_url=it.get("source_url"),
                    estimated_minutes=it.get("estimated_minutes", 60),
                    difficulty=it.get("difficulty", 1),
                    topic=it["topic"],
                    skill_id=skill_id,
                    prerequisites=it.get("prerequisites", []),
                    optional=it.get("optional", False),
                    status=it.get("status", "draft"),
                    sequence_order=it.get("sequence_order", 0),
                    extra_data=it.get("extra_data", {}),
                )
                session.add(item)

        seeded_count += 1

    await session.commit()
    return seeded_count


async def main():
    json_path = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "roadmap_templates.json"
    async with async_session_factory() as session:
        count = await seed_roadmaps(session, json_path)
        print(f"Successfully seeded/updated {count} roadmap templates from {json_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
