"""Seed script for interview questions from interview_questions.json."""
import asyncio
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.career import Career
from app.models.interview import InterviewQuestion


async def seed_interview_questions(session: AsyncSession, json_path: Path) -> int:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    seeded_count = 0

    for item in questions:
        career = None
        if item.get("career_code"):
            c_code = item["career_code"]
            c_stmt = select(Career).where(Career.code == c_code)
            c_res = await session.execute(c_stmt)
            career = c_res.scalar_one_or_none()

        stmt = select(InterviewQuestion).where(InterviewQuestion.text == item["text"])
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.career_id = career.id if career else None
            existing.type = item["type"]
            existing.level = item["level"]
            existing.key_points = item["key_points"]
            existing.sample_answer = item.get("sample_answer")
            existing.source_note = item.get("source_note")
            if existing.status != "verified":
                existing.status = item.get("status", "draft")
        else:
            q = InterviewQuestion(
                id=uuid4(),
                career_id=career.id if career else None,
                type=item["type"],
                level=item["level"],
                text=item["text"],
                key_points=item["key_points"],
                sample_answer=item.get("sample_answer"),
                status=item.get("status", "draft"),
                source_note=item.get("source_note"),
            )
            session.add(q)

        seeded_count += 1

    await session.commit()
    return seeded_count


async def main():
    json_path = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "interview_questions.json"
    async with async_session_factory() as session:
        count = await seed_interview_questions(session, json_path)
        print(f"Successfully seeded/updated {count} interview questions from {json_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
