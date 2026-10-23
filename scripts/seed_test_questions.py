import asyncio
import json
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.adaptive_test import TestQuestionBank


async def seed_test_questions(session: AsyncSession, json_path: Path) -> int:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    seeded_count = 0

    for q in questions:
        qid = UUID(q["id"])
        stmt = select(TestQuestionBank).where(TestQuestionBank.id == qid)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.type = q["type"]
            existing.topic = q["topic"]
            existing.subtopic = q.get("subtopic")
            existing.language = q.get("language")
            existing.difficulty = q["difficulty"]
            existing.question_text = q["question_text"]
            existing.options = q["options"]
            existing.correct_option_id = q["correct_option_id"]
            existing.explanation = q["explanation"]
            existing.source_note = q["source_note"]
            existing.career_cluster = q.get("career_cluster")
            # Preserve verified status if already verified
            if existing.status != "verified":
                existing.status = q.get("status", "draft")
        else:
            new_q = TestQuestionBank(
                id=qid,
                type=q["type"],
                topic=q["topic"],
                subtopic=q.get("subtopic"),
                language=q.get("language"),
                difficulty=q["difficulty"],
                question_text=q["question_text"],
                options=q["options"],
                correct_option_id=q["correct_option_id"],
                explanation=q["explanation"],
                source_note=q["source_note"],
                status=q.get("status", "draft"),
                career_cluster=q.get("career_cluster"),
            )
            session.add(new_q)

        seeded_count += 1

    await session.commit()
    return seeded_count


async def main() -> None:
    seed_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "test_questions.json"
    if not seed_file.is_file():
        print(f"Error: seed file not found at {seed_file}")
        return

    async with async_session_factory() as session:
        count = await seed_test_questions(session, seed_file)
        print(f"Successfully seeded {count} adaptive test questions.")


if __name__ == "__main__":
    asyncio.run(main())
