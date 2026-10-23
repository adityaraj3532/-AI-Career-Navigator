import asyncio
import json
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.assessment import AssessmentQuestion, AssessmentVersion

logger = logging.getLogger("scripts.seed_assessment")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def seed_assessment_data(session: AsyncSession, json_path: Path) -> AssessmentVersion:
    if not json_path.is_file():
        raise FileNotFoundError(f"Seed file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    version_number = data["version_number"]
    title = data["title"]
    description = data["description"]
    questions_data = data["questions"]

    # 1. Check if version already exists
    stmt = select(AssessmentVersion).where(AssessmentVersion.version_number == version_number)
    result = await session.execute(stmt)
    version_record = result.scalar_one_or_none()

    if not version_record:
        logger.info("Creating assessment version %d: '%s'", version_number, title)
        version_record = AssessmentVersion(
            version_number=version_number,
            title=title,
            description=description,
            is_active=True,
        )
        session.add(version_record)
        await session.flush()
    else:
        logger.info("Assessment version %d exists. Updating metadata...", version_number)
        version_record.title = title
        version_record.description = description
        version_record.is_active = True
        await session.flush()

    # 2. Upsert questions
    q_stmt = select(AssessmentQuestion).where(
        AssessmentQuestion.assessment_version_id == version_record.id
    )
    q_res = await session.execute(q_stmt)
    existing_questions = {q.question_order: q for q in q_res.scalars().all()}

    inserted_count = 0
    updated_count = 0

    for q_item in questions_data:
        order = q_item["order"]
        text = q_item["text"]
        dimension = q_item["dimension"]
        reverse = q_item["reverse_scored"]

        if order in existing_questions:
            eq = existing_questions[order]
            eq.text = text
            eq.dimension = dimension
            eq.reverse_scored = reverse
            eq.is_active = True
            updated_count += 1
        else:
            new_q = AssessmentQuestion(
                assessment_version_id=version_record.id,
                question_order=order,
                text=text,
                dimension=dimension,
                reverse_scored=reverse,
                is_active=True,
            )
            session.add(new_q)
            inserted_count += 1

    await session.commit()
    logger.info(
        "Seeding complete for version %d! Inserted: %d, Updated: %d, Total: %d questions.",
        version_number,
        inserted_count,
        updated_count,
        len(questions_data),
    )
    return version_record


async def main() -> None:
    seed_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "assessment_questions.json"
    async with async_session_factory() as session:
        await seed_assessment_data(session, seed_file)


if __name__ == "__main__":
    asyncio.run(main())
