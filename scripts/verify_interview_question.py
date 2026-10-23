import argparse
import asyncio
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.career import Career
from app.models.interview import InterviewQuestion


async def verify_interview_questions(
    session: AsyncSession,
    reviewer: str,
    question_id: str | None = None,
    career_code: str | None = None,
    question_type: str | None = None,
    all_questions: bool = False,
) -> int:
    now = datetime.now(timezone.utc)
    stmt = select(InterviewQuestion)

    if question_id:
        stmt = stmt.where(InterviewQuestion.id == UUID(question_id))
    elif career_code:
        c_stmt = select(Career).where(Career.code == career_code)
        c_res = await session.execute(c_stmt)
        career = c_res.scalar_one_or_none()
        if not career:
            print(f"Career with code '{career_code}' not found.")
            return 0
        stmt = stmt.where(InterviewQuestion.career_id == career.id)
        if question_type:
            stmt = stmt.where(InterviewQuestion.type == question_type)
    elif question_type:
        stmt = stmt.where(InterviewQuestion.type == question_type)
    elif not all_questions:
        print("Please specify --question-id, --career, --type, or --all.")
        return 0

    res = await session.execute(stmt)
    questions = res.scalars().all()

    if not questions:
        print("No matching interview questions found.")
        return 0

    for q in questions:
        q.status = "verified"
        q.last_verified_by = reviewer
        q.last_verified_at = now

    await session.commit()
    print(f"Successfully verified {len(questions)} interview question(s) by reviewer '{reviewer}'.")
    return len(questions)


def main():
    parser = argparse.ArgumentParser(description="CLI to mark interview questions as verified.")
    parser.add_argument("--reviewer", required=True, help="Name or email of the reviewer verifying the questions.")
    parser.add_argument("--question-id", help="UUID of a specific interview question to verify.")
    parser.add_argument("--career", help="Career code (e.g. SOFTWARE_DEVELOPER) to verify questions for.")
    parser.add_argument("--type", choices=["technical", "hr"], help="Question type to verify.")
    parser.add_argument("--all", action="store_true", help="Verify all interview questions in the database.")

    args = parser.parse_args()

    async def run():
        async with async_session_factory() as session:
            await verify_interview_questions(
                session=session,
                reviewer=args.reviewer,
                question_id=args.question_id,
                career_code=args.career,
                question_type=args.type,
                all_questions=args.all,
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
