from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.adaptive_test import TestAttempt, TestAttemptAnswer
from app.models.user import User
from app.repositories.adaptive_test_repository import AdaptiveTestRepository
from app.repositories.career_repository import CareerRepository
from app.schemas.adaptive_test import (
    FinishTestResponse,
    QuestionOptionSchema,
    QuestionPublicSchema,
    StartTestRequest,
    StartTestResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services.adaptive_test_engine import (
    calculate_next_difficulty,
    evaluate_final_level,
)


class AdaptiveTestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AdaptiveTestRepository(session)
        self.career_repo = CareerRepository(session)

    async def start_test(
        self,
        user: User,
        req: StartTestRequest,
    ) -> StartTestResponse:
        settings = get_settings()
        allow_drafts_careers = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)
        allow_drafts_questions = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_QUESTIONS)

        # 1. Career verification check
        career = await self.career_repo.get_by_id(req.career_id, allow_drafts=allow_drafts_careers, eager_load=False)
        if not career:
            raise AppException(status_code=404, message=f"Career '{req.career_id}' not found or not verified.")

        now = datetime.now(timezone.utc)

        # 2. Rate limit on start (starts in past hour)
        one_hour_ago = now - timedelta(hours=1)
        recent_starts = await self.repo.count_user_starts_since(user.id, one_hour_ago)
        if recent_starts >= settings.TEST_MAX_STARTS_PER_HOUR:
            raise AppException(
                status_code=429,
                message=f"Rate limit exceeded: maximum {settings.TEST_MAX_STARTS_PER_HOUR} test starts allowed per hour.",
            )

        # 3. Active attempt check
        active_attempt = await self.repo.get_active_attempt(user.id, req.topic)
        if active_attempt:
            if active_attempt.expires_at < now:
                active_attempt.status = "expired"
                await self.repo.save_attempt(active_attempt)
            else:
                raise AppException(
                    status_code=400,
                    message=f"An active test attempt already exists for topic '{req.topic}'. Finish or wait for it to expire.",
                )

        # 4. Retake cooldown check
        finished_attempt = await self.repo.get_recent_finished_attempt(user.id, req.topic)
        if finished_attempt and finished_attempt.finished_at:
            cooldown_delta = timedelta(minutes=settings.TEST_RETAKE_COOLDOWN_MINUTES)
            if (now - finished_attempt.finished_at) < cooldown_delta:
                remaining_secs = int((finished_attempt.finished_at + cooldown_delta - now).total_seconds())
                remaining_mins = max(1, remaining_secs // 60)
                raise AppException(
                    status_code=400,
                    message=f"Retake cooldown active for topic '{req.topic}'. Please wait {remaining_mins} more minute(s).",
                )

        # 5. Check available verified questions
        available_count = await self.repo.count_available_questions(
            topic=req.topic,
            allow_drafts=allow_drafts_questions,
            language=req.language,
        )
        target_questions = 6
        if available_count < target_questions:
            raise AppException(
                status_code=400,
                message=(
                    f"Not enough verified questions available for topic '{req.topic}'. "
                    f"Available: {available_count}, Required: {target_questions}."
                ),
            )

        # 6. Pick first question (starting at difficulty 2)
        recent_question_ids = await self.repo.get_user_recent_question_ids(user.id, req.topic)
        first_q = await self.repo.pick_next_question(
            topic=req.topic,
            target_difficulty=2,
            allow_drafts=allow_drafts_questions,
            language=req.language,
            exclude_question_ids=set(),
            recently_seen_ids=recent_question_ids,
        )
        if not first_q:
            raise AppException(
                status_code=400,
                message=f"No questions available to start test for topic '{req.topic}'.",
            )

        # 7. Create TestAttempt
        time_limit_secs = settings.TEST_TIME_LIMIT_MINUTES * 60
        new_attempt = TestAttempt(
            user_id=user.id,
            career_id=career.id,
            type=req.type,
            topic=req.topic,
            language=req.language,
            status="in_progress",
            current_difficulty=2,
            target_questions=target_questions,
            time_limit_seconds=time_limit_secs,
            total_answered=0,
            started_at=now,
            expires_at=now + timedelta(seconds=time_limit_secs),
        )
        saved_attempt = await self.repo.save_attempt(new_attempt)

        # Build public question (NO correct_option_id, NO explanation!)
        public_q = QuestionPublicSchema(
            id=first_q.id,
            difficulty=first_q.difficulty,
            question_text=first_q.question_text,
            options=[QuestionOptionSchema(**opt) for opt in first_q.options],
        )

        return StartTestResponse(
            test_id=saved_attempt.id,
            career_id=saved_attempt.career_id,
            type=saved_attempt.type,
            topic=saved_attempt.topic,
            language=saved_attempt.language,
            status=saved_attempt.status,
            time_limit_seconds=saved_attempt.time_limit_seconds,
            total_questions=saved_attempt.target_questions,
            current_question_index=1,
            current_question=public_q,
        )

    async def submit_answer(
        self,
        user: User,
        attempt_id: UUID,
        req: SubmitAnswerRequest,
    ) -> SubmitAnswerResponse:
        settings = get_settings()
        allow_drafts_questions = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_QUESTIONS)

        # 1. Ownership & existence
        attempt = await self.repo.get_attempt_by_id(attempt_id)
        if not attempt or attempt.user_id != user.id:
            raise AppException(status_code=404, message=f"Test attempt '{attempt_id}' not found.")

        now = datetime.now(timezone.utc)

        # 2. Expiration and status check
        if attempt.status == "finished":
            raise AppException(status_code=400, message="Test attempt is already finished.")
        if attempt.status == "expired" or attempt.expires_at < now:
            if attempt.status != "expired":
                attempt.status = "expired"
                await self.repo.save_attempt(attempt)
            raise AppException(status_code=400, message="Test attempt has expired.")

        # 3. Question check
        question = await self.repo.get_question_by_id(req.question_id)
        if not question:
            raise AppException(status_code=404, message=f"Question '{req.question_id}' not found.")

        # 4. Idempotency / Double answer check
        existing_answer = await self.repo.get_answer(attempt.id, req.question_id)
        if existing_answer:
            if existing_answer.selected_option_id == req.selected_option_id:
                # Idempotent re-submission
                is_last = attempt.total_answered >= attempt.target_questions
                next_q = None
                if not is_last:
                    # Serve existing next question
                    exclude_ids = set(a.question_id for a in attempt.answers)
                    raw_next = await self.repo.pick_next_question(
                        topic=attempt.topic,
                        target_difficulty=attempt.current_difficulty,
                        allow_drafts=allow_drafts_questions,
                        language=attempt.language,
                        exclude_question_ids=exclude_ids,
                    )
                    if raw_next:
                        next_q = QuestionPublicSchema(
                            id=raw_next.id,
                            difficulty=raw_next.difficulty,
                            question_text=raw_next.question_text,
                            options=[QuestionOptionSchema(**opt) for opt in raw_next.options],
                        )

                return SubmitAnswerResponse(
                    is_correct=existing_answer.is_correct,
                    explanation=question.explanation,
                    next_difficulty=attempt.current_difficulty,
                    current_question_index=existing_answer.question_order,
                    total_questions=attempt.target_questions,
                    can_finish=is_last,
                    next_question=next_q,
                )
            else:
                raise AppException(
                    status_code=400,
                    message="Question has already been answered with a different option.",
                )

        # 5. Evaluate answer
        is_correct = (question.correct_option_id == req.selected_option_id)
        order = attempt.total_answered + 1

        new_ans = TestAttemptAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            question_order=order,
            difficulty_at_question=question.difficulty,
            selected_option_id=req.selected_option_id,
            is_correct=is_correct,
            time_taken_seconds=req.time_taken_seconds,
        )
        await self.repo.add_answer(new_ans)

        # 6. Adaptive progression
        next_diff = calculate_next_difficulty(attempt.current_difficulty, is_correct)
        attempt.current_difficulty = next_diff
        attempt.total_answered = order
        await self.repo.save_attempt(attempt)

        is_last = attempt.total_answered >= attempt.target_questions
        next_q_public: Optional[QuestionPublicSchema] = None

        if not is_last:
            exclude_ids = set(a.question_id for a in attempt.answers) | {question.id}
            recent_ids = await self.repo.get_user_recent_question_ids(user.id, attempt.topic)
            next_q = await self.repo.pick_next_question(
                topic=attempt.topic,
                target_difficulty=next_diff,
                allow_drafts=allow_drafts_questions,
                language=attempt.language,
                exclude_question_ids=exclude_ids,
                recently_seen_ids=recent_ids,
            )
            if next_q:
                next_q_public = QuestionPublicSchema(
                    id=next_q.id,
                    difficulty=next_q.difficulty,
                    question_text=next_q.question_text,
                    options=[QuestionOptionSchema(**opt) for opt in next_q.options],
                )

        return SubmitAnswerResponse(
            is_correct=is_correct,
            explanation=question.explanation,
            next_difficulty=next_diff,
            current_question_index=order,
            total_questions=attempt.target_questions,
            can_finish=is_last,
            next_question=next_q_public,
        )

    async def finish_test(
        self,
        user: User,
        attempt_id: UUID,
    ) -> FinishTestResponse:
        # 1. Ownership & existence
        attempt = await self.repo.get_attempt_by_id(attempt_id)
        if not attempt or attempt.user_id != user.id:
            raise AppException(status_code=404, message=f"Test attempt '{attempt_id}' not found.")

        # 2. Idempotency: if already finished, return results
        if attempt.status == "finished":
            answers_data = [
                {"difficulty": a.difficulty_at_question, "is_correct": a.is_correct}
                for a in attempt.answers
            ]
            _, _, _, _, recs, _ = evaluate_final_level(answers_data)
            return FinishTestResponse(
                test_id=attempt.id,
                status=attempt.status,
                score_percentage=attempt.score_percentage or 0,
                total_correct=attempt.total_correct or 0,
                total_questions=attempt.target_questions,
                demonstrated_level=attempt.demonstrated_level or "beginner",
                confidence=attempt.confidence or "low",
                recommendations=recs,
                disclaimer_note=attempt.disclaimer_note or "This level is a preliminary estimate from a short adaptive diagnostic test.",
                finished_at=attempt.finished_at or datetime.now(timezone.utc),
            )

        now = datetime.now(timezone.utc)
        if attempt.status == "expired" or attempt.expires_at < now:
            if attempt.status != "expired":
                attempt.status = "expired"
                await self.repo.save_attempt(attempt)
            raise AppException(status_code=400, message="Test attempt has expired.")

        # 3. Calculate final proficiency metrics
        answers_data = [
            {"difficulty": a.difficulty_at_question, "is_correct": a.is_correct}
            for a in attempt.answers
        ]
        level, conf, score_pct, total_corr, recs, disclaimer = evaluate_final_level(answers_data)

        attempt.status = "finished"
        attempt.demonstrated_level = level
        attempt.confidence = conf
        attempt.score_percentage = score_pct
        attempt.total_correct = total_corr
        attempt.disclaimer_note = disclaimer
        attempt.finished_at = now

        await self.repo.save_attempt(attempt)

        # Compute subtopic scores from answers
        subtopic_counts: Dict[str, Dict[str, int]] = {}
        for a in attempt.answers:
            sub = a.question.subtopic if getattr(a, "question", None) else None
            if sub:
                counts = subtopic_counts.setdefault(sub, {"total": 0, "correct": 0})
                counts["total"] += 1
                if a.is_correct:
                    counts["correct"] += 1

        subtopic_scores = {
            sub: round((counts["correct"] / counts["total"]) * 100)
            for sub, counts in subtopic_counts.items()
            if counts["total"] > 0
        }

        # Atomically ingest test result into skill tracker within the same transaction
        from app.services.skill_service import SkillService
        skill_service = SkillService(self.repo.session)
        await skill_service.ingest_test_result(
            user_id=user.id,
            attempt_id=attempt.id,
            topic=attempt.topic,
            language=attempt.language,
            demonstrated_level=level,
            score_percentage=score_pct,
            subtopic_scores=subtopic_scores,
        )

        return FinishTestResponse(
            test_id=attempt.id,
            status=attempt.status,
            score_percentage=score_pct,
            total_correct=total_corr,
            total_questions=attempt.target_questions,
            demonstrated_level=level,
            confidence=conf,
            recommendations=recs,
            disclaimer_note=disclaimer,
            finished_at=now,
        )
