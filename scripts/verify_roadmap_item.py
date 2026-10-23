import argparse
import asyncio
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.career import Career
from app.models.roadmap import RoadmapTemplate, TemplateItem


async def verify_items(
    session: AsyncSession,
    reviewer: str,
    item_id: str | None = None,
    item_code: str | None = None,
    career_code: str | None = None,
    all_items: bool = False,
) -> int:
    now = datetime.now(timezone.utc)

    stmt = select(TemplateItem)
    if item_id:
        stmt = stmt.where(TemplateItem.id == UUID(item_id))
    elif item_code:
        stmt = stmt.where(TemplateItem.item_code == item_code)
    elif career_code:
        c_stmt = select(Career).where(Career.code == career_code)
        c_res = await session.execute(c_stmt)
        career = c_res.scalar_one_or_none()
        if not career:
            print(f"Career '{career_code}' not found.")
            return 0
        t_stmt = select(RoadmapTemplate.id).where(RoadmapTemplate.career_id == career.id)
        t_res = await session.execute(t_stmt)
        template_ids = t_res.scalars().all()
        stmt = stmt.where(TemplateItem.template_id.in_(template_ids))
    elif not all_items:
        print("Specify --item-id, --item-code, --career, or --all.")
        return 0

    res = await session.execute(stmt)
    items = res.scalars().all()

    if not items:
        print("No matching template items found.")
        return 0

    template_ids_to_verify = set()
    for it in items:
        it.status = "verified"
        it.reviewer = reviewer
        it.last_verified_at = now
        template_ids_to_verify.add(it.template_id)

    # Also mark parent templates verified
    for tid in template_ids_to_verify:
        tmpl_stmt = select(RoadmapTemplate).where(RoadmapTemplate.id == tid)
        t_res = await session.execute(tmpl_stmt)
        tmpl = t_res.scalar_one_or_none()
        if tmpl:
            tmpl.status = "verified"
            tmpl.reviewer = reviewer
            tmpl.last_verified_at = now

    await session.commit()
    print(f"Verified {len(items)} roadmap items by '{reviewer}'.")
    return len(items)


def main():
    parser = argparse.ArgumentParser(description="Verify roadmap template items for production release.")
    parser.add_argument("--item-id", help="UUID of specific template item to verify")
    parser.add_argument("--item-code", help="Item code to verify (e.g. dsa_arrays_two_sum)")
    parser.add_argument("--career", help="Career code to verify all template items for (e.g. SWE)")
    parser.add_argument("--all", action="store_true", help="Verify all template items across all templates")
    parser.add_argument("--reviewer", default="admin_curator", help="Reviewer identity string")

    args = parser.parse_args()

    async def run():
        async with async_session_factory() as session:
            await verify_items(
                session=session,
                reviewer=args.reviewer,
                item_id=args.item_id,
                item_code=args.item_code,
                career_code=args.career,
                all_items=args.all,
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
