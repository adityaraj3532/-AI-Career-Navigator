import argparse
import asyncio
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.adaptive_test import TestQuestionBank


async def verify_questions(
    session: AsyncSession,
    question_id: str | None = None,
    topic: str | None = None,
    verify_all: bool = False,
    reviewer: str = "curriculum_lead",
) -> int:
    now = datetime.now(timezone.utc)

    if question_id:
        qid = UUID(question_id)
        stmt = (
            update(TestQuestionBank)
            .where(TestQuestionBank.id == qid)
            .values(status="verified", reviewer=reviewer, verified_at=now)
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount

    if topic:
        stmt = (
            update(TestQuestionBank)
            .where(TestQuestionBank.topic == topic)
            .values(status="verified", reviewer=reviewer, verified_at=now)
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount

    if verify_all:
        stmt = (
            update(TestQuestionBank)
            .values(status="verified", reviewer=reviewer, verified_at=now)
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount

    return 0


async def main() -> None:
    parser = argparse.ArgumentParser(description="Verify diagnostic test questions in the database.")
    parser.add_argument("--id", help="UUID of specific question to verify")
    parser.add_argument("--topic", help="Topic to verify all questions for (e.g. 'dsa', 'python')")
    parser.add_argument("--all", action="store_true", help="Verify all questions in question bank")
    parser.add_argument("--reviewer", default="curriculum_lead", help="Reviewer identifier")

    args = parser.parse_args()

    if not args.id and not args.topic and not args.all:
        print("Specify --id, --topic, or --all to verify questions.")
        return

    async with async_session_factory() as session:
        count = await verify_questions(
            session=session,
            question_id=args.id,
            topic=args.topic,
            verify_all=args.all,
            reviewer=args.reviewer,
        )
        print(f"Verified {count} questions successfully with reviewer='{args.reviewer}'.")


if __name__ == "__main__":
    asyncio.run(main())
