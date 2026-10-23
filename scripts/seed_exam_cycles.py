import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.career import Exam
from app.models.exam_cycle import ExamCycle


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def seed_exam_cycles(session: AsyncSession, json_path: Path) -> int:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cycles_data = data.get("exam_cycles", [])
    seeded_count = 0

    for item in cycles_data:
        code = item["exam_code"]
        stmt = select(Exam).where(Exam.code == code)
        res = await session.execute(stmt)
        exam = res.scalar_one_or_none()
        if not exam:
            # Skip if exam not in catalog yet
            continue

        year = item["year"]
        cycle_stmt = select(ExamCycle).where(
            ExamCycle.exam_id == exam.id,
            ExamCycle.year == year,
        )
        cres = await session.execute(cycle_stmt)
        existing = cres.scalar_one_or_none()

        reg_start = _parse_dt(item.get("registration_start"))
        reg_end = _parse_dt(item.get("registration_end"))
        exam_date = _parse_dt(item.get("exam_date"))

        if existing:
            existing.registration_start = reg_start
            existing.registration_end = reg_end
            existing.exam_date = exam_date
            existing.source_url = item["source_url"]
            if existing.status != "verified":
                existing.status = item.get("status", "draft")
        else:
            new_cycle = ExamCycle(
                exam_id=exam.id,
                year=year,
                registration_start=reg_start,
                registration_end=reg_end,
                exam_date=exam_date,
                source_url=item["source_url"],
                status=item.get("status", "draft"),
            )
            session.add(new_cycle)

        seeded_count += 1

    await session.commit()
    return seeded_count


async def main():
    json_path = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "exam_cycles.json"
    async with async_session_factory() as session:
        count = await seed_exam_cycles(session, json_path)
        print(f"Successfully seeded/updated {count} exam cycles from {json_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
