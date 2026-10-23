import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.llm.gateway import LLMGateway
from app.models.assessment import AssessmentAttempt, AssessmentResult, AssessmentVersion
from app.models.user import User
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.career_repository import CareerRepository
from app.schemas.assessment import (
    AssessmentExplanationAISchema,
    AssessmentQARequest,
    AssessmentQAResponse,
    AssessmentResultResponse,
    AttemptResponse,
    CareerSuggestionItem,
    ChooseCareerRequest,
    ChooseCareerResponse,
    QuestionResponse,
    QuestionsListResponse,
    SaveAnswersRequest,
    SavedAnswerDetail,
)
from app.services.scoring_service import (
    compute_riasec_scores,
    derive_holland_code,
    derive_traits_and_skills,
    map_streams_for_grade_11_12,
    rank_careers,
)

logger = logging.getLogger("app.services.assessment")


class AssessmentService:
    def __init__(
        self,
        session: AsyncSession,
        gateway: Optional[LLMGateway] = None,
    ) -> None:
        self.session = session
        self.repo = AssessmentRepository(session)
        self.career_repo = CareerRepository(session)
        self.gateway = gateway or LLMGateway()

    async def get_active_questions(self) -> QuestionsListResponse:
        version = await self.repo.get_active_version()
        if not version:
            raise AppException(
                status_code=503,
                code="NO_ACTIVE_ASSESSMENT_VERSION",
                message="No active career assessment version is currently available.",
            )

        questions = await self.repo.get_questions_for_version(version.id)
        question_responses = [
            QuestionResponse(
                id=q.id,
                question_order=q.question_order,
                text=q.text,
                dimension=q.dimension,
                scale_min=1,
                scale_max=5,
            )
            for q in questions
        ]

        return QuestionsListResponse(
            assessment_version_id=version.id,
            version_number=version.version_number,
            title=version.title,
            description=version.description,
            total_questions=len(question_responses),
            questions=question_responses,
        )

    async def get_or_create_draft_attempt(self, user_id: UUID) -> AttemptResponse:
        attempt = await self.repo.get_active_draft_attempt(user_id)
        if not attempt:
            version = await self.repo.get_active_version()
            if not version:
                raise AppException(
                    status_code=503,
                    code="NO_ACTIVE_ASSESSMENT_VERSION",
                    message="No active assessment version available to start an attempt.",
                )
            attempt = await self.repo.create_attempt(user_id, version.id)
            await self.session.commit()
            # Reload with relationships
            attempt = await self.repo.get_active_draft_attempt(user_id)

        return self._format_attempt_response(attempt)

    async def save_answers(
        self,
        user_id: UUID,
        req: SaveAnswersRequest,
        attempt_id: Optional[UUID] = None,
    ) -> AttemptResponse:
        if attempt_id is not None:
            attempt = await self.repo.get_attempt_by_id(attempt_id, user_id)
            if not attempt:
                raise AppException(
                    status_code=404,
                    code="ATTEMPT_NOT_FOUND",
                    message="Assessment attempt not found or unauthorized.",
                )
        else:
            attempt = await self.repo.get_active_draft_attempt(user_id)
            if not attempt:
                version = await self.repo.get_active_version()
                if not version:
                    raise AppException(
                        status_code=503,
                        code="NO_ACTIVE_ASSESSMENT_VERSION",
                        message="No active assessment version available.",
                    )
                attempt = await self.repo.create_attempt(user_id, version.id)
                await self.session.commit()

        if attempt.status != "draft":
            raise AppException(
                status_code=400,
                code="ATTEMPT_ALREADY_SUBMITTED",
                message="Cannot modify answers on a submitted assessment attempt.",
            )

        valid_questions = await self.repo.get_questions_for_version(attempt.assessment_version_id)
        valid_q_map = {q.id: q for q in valid_questions}

        for item in req.answers:
            if item.question_id not in valid_q_map:
                raise AppException(
                    status_code=400,
                    code="INVALID_QUESTION_ID",
                    message=f"Question ID '{item.question_id}' does not belong to this assessment version.",
                )

        await self.repo.upsert_answers(attempt.id, req.answers)
        await self.session.commit()

        updated_attempt = await self.repo.get_attempt_by_id(attempt.id, user_id)
        return self._format_attempt_response(updated_attempt)

    async def submit_assessment(
        self,
        user: User,
        attempt_id: Optional[UUID] = None,
    ) -> AssessmentResultResponse:
        # 1. Resolve attempt
        if attempt_id is not None:
            attempt = await self.repo.get_attempt_by_id(attempt_id, user.id)
            if not attempt:
                raise AppException(
                    status_code=404,
                    code="ATTEMPT_NOT_FOUND",
                    message="Assessment attempt not found or unauthorized.",
                )
        else:
            attempt = await self.repo.get_active_draft_attempt(user.id)
            if not attempt:
                # Check if there is an existing submitted attempt with results
                latest_result = await self.repo.get_latest_result(user.id)
                if latest_result:
                    return self._format_result_response(latest_result)
                raise AppException(
                    status_code=404,
                    code="ATTEMPT_NOT_FOUND",
                    message="No active draft assessment attempt found to submit.",
                )

        # 2. Idempotent check: if already submitted, return existing result
        if attempt.status == "submitted":
            existing_result = await self.repo.get_result_by_attempt_id(attempt.id)
            if existing_result:
                return self._format_result_response(existing_result)

        # 3. Check that all questions are answered
        valid_questions = await self.repo.get_questions_for_version(attempt.assessment_version_id)
        if not valid_questions:
            raise AppException(
                status_code=500,
                code="VERSION_WITHOUT_QUESTIONS",
                message="Assessment version has no configured questions.",
            )

        answered_map = {ans.question_id: ans.value for ans in attempt.answers}
        missing_ids = [q.id for q in valid_questions if q.id not in answered_map]

        if missing_ids:
            raise AppException(
                status_code=400,
                code="INCOMPLETE_ASSESSMENT",
                message=f"Assessment is incomplete. {len(missing_ids)} questions remaining.",
                details={
                    "missing_question_ids": [str(x) for x in missing_ids],
                    "missing_count": len(missing_ids),
                    "total_required": len(valid_questions),
                },
            )

        # 4. Pure deterministic scoring
        questions_metadata = [
            {
                "question_order": q.question_order,
                "dimension": q.dimension,
                "reverse_scored": q.reverse_scored,
            }
            for q in valid_questions
        ]
        answers_by_order = {q.question_order: answered_map[q.id] for q in valid_questions}

        scores = compute_riasec_scores(answers_by_order, questions_metadata)
        holland_code, holland_code_label = derive_holland_code(scores)
        traits, skills = derive_traits_and_skills(holland_code)

        # 5. Stream mapping for class_11_12
        recommended_streams: Optional[List[str]] = None
        if user.education_level == "class_11_12":
            recommended_streams = map_streams_for_grade_11_12(scores, holland_code)

        # 6. Career retrieval & ranking
        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)
        available_careers = await self.career_repo.get_careers(allow_drafts=allow_drafts)

        if not available_careers:
            raise AppException(
                status_code=503,
                code="NO_AVAILABLE_CAREERS",
                message="No verified careers are available for matching.",
            )

        careers_dicts = [
            {
                "id": c.id,
                "code": c.code,
                "title": c.title,
                "cluster": c.cluster,
                "overview": c.overview,
                "source_url": c.source_url,
                "dimension_weights": c.dimension_weights,
            }
            for c in available_careers
        ]

        top_careers = rank_careers(scores, careers_dicts, top_n=3)
        valid_career_ids = {c["career_id"] for c in top_careers}

        # 7. AI Explanation with LLM Gateway
        # Note: Only numbers and career summaries are provided; no name, email, or free text
        career_summaries = []
        for c in top_careers:
            career_summaries.append(
                f"- ID: {c['career_id']}\n"
                f"  Title: {c['title']} ({c['cluster']})\n"
                f"  Match Score: {int(c['similarity_score'] * 100)}%\n"
                f"  Overview: {c['overview']}"
            )
        catalog_str = "\n\n".join(career_summaries)

        scores_str = "\n".join(f"- {dim}: {score}" for dim, score in scores.items())
        traits_str = ", ".join(traits)
        skills_str = ", ".join(skills)

        def fallback_factory() -> AssessmentExplanationAISchema:
            return AssessmentExplanationAISchema(
                summary_explanation=(
                    f"Your assessment demonstrates strong alignment with the {holland_code} "
                    f"({holland_code_label}) profile. Your dimensional strengths emphasize "
                    f"{traits[0].lower()} and {skills[0].lower()}, thriving in environments with clear "
                    f"vocational objectives and opportunities for professional mastery."
                ),
                career_reasons={
                    c["career_id"]: (
                        f"{c['title']} is an outstanding match ({int(c['similarity_score'] * 100)}% alignment) "
                        f"for your {holland_code} profile in the {c['cluster']} sector."
                    )
                    for c in top_careers
                },
            )

        def post_validator(ai_data: AssessmentExplanationAISchema) -> bool:
            if not ai_data.career_reasons:
                return False
            # Verify that every career ID referenced in reasons exists in our code-chosen top careers
            for cid in ai_data.career_reasons.keys():
                if cid not in valid_career_ids:
                    return False
            return True

        gateway_resp = await self.gateway.execute_prompt(
            prompt_name="assessment_explanation",
            prompt_version=1,
            schema=AssessmentExplanationAISchema,
            fallback_factory=fallback_factory,
            system_variables={
                "holland_code": holland_code,
                "holland_code_label": holland_code_label,
                "dimension_scores": scores_str,
                "traits": traits_str,
                "skills": skills_str,
                "career_catalog": catalog_str,
            },
            post_validator=post_validator,
        )

        ai_data = gateway_resp.data

        # Build career suggestions
        career_suggestions = []
        for c in top_careers:
            cid = c["career_id"]
            reason = ai_data.career_reasons.get(
                cid,
                f"{c['title']} aligns closely with your {holland_code} profile.",
            )
            career_suggestions.append({
                "career_id": UUID(cid),
                "code": c["code"],
                "title": c["title"],
                "cluster": c["cluster"],
                "overview": c["overview"],
                "source_url": c["source_url"],
                "similarity_score": c["similarity_score"],
                "reason": reason,
            })

        # 8. Persist Result & Update Attempt
        try:
            next_version = await self.repo.get_next_result_version(user.id)
            now = datetime.now(timezone.utc)
            result = AssessmentResult(
                user_id=user.id,
                attempt_id=attempt.id,
                assessment_version_id=attempt.assessment_version_id,
                version=next_version,
                dimension_scores=scores,
                holland_code=holland_code,
                holland_code_label=holland_code_label,
                traits=traits,
                skills=skills,
                recommended_streams=recommended_streams,
                career_suggestions=career_suggestions,
                ai_explanation=ai_data.summary_explanation,
                disclaimer_note=(
                    "These results provide career navigation guidance and vocational exploration insights; "
                    "they are not a psychological evaluation or clinical diagnosis."
                ),
                created_at=now,
            )
            saved_result = await self.repo.save_result(result)
            attempt.status = "submitted"
            attempt.submitted_at = now
            await self.session.commit()
            return self._format_result_response(saved_result)

        except IntegrityError:
            # Handle concurrent submission race conditions safely
            await self.session.rollback()
            existing_result = await self.repo.get_result_by_attempt_id(attempt.id)
            if existing_result:
                return self._format_result_response(existing_result)
            raise

    async def get_latest_result(self, user_id: UUID) -> AssessmentResultResponse:
        result = await self.repo.get_latest_result(user_id)
        if not result:
            raise AppException(
                status_code=404,
                code="RESULT_NOT_FOUND",
                message="No assessment results found for user.",
            )
        return self._format_result_response(result)

    async def get_all_results(self, user_id: UUID) -> List[AssessmentResultResponse]:
        results = await self.repo.get_results_for_user(user_id)
        return [self._format_result_response(r) for r in results]

    async def get_result_by_id(self, result_id: UUID, user_id: UUID) -> AssessmentResultResponse:
        result = await self.repo.get_result_by_id(result_id, user_id)
        if not result:
            raise AppException(
                status_code=404,
                code="RESULT_NOT_FOUND",
                message="Assessment result not found or unauthorized.",
            )
        return self._format_result_response(result)

    def _format_attempt_response(self, attempt: AssessmentAttempt) -> AttemptResponse:
        version: AssessmentVersion = attempt.assessment_version
        version_number = version.version_number if version else 1
        total_questions = len(version.questions) if version and version.questions else 30

        saved_details: list[SavedAnswerDetail] = []
        if attempt.answers:
            for ans in attempt.answers:
                q = ans.question
                saved_details.append(
                    SavedAnswerDetail(
                        question_id=ans.question_id,
                        question_order=q.question_order if q else 0,
                        dimension=q.dimension if q else "Unknown",
                        value=ans.value,
                        updated_at=ans.updated_at,
                    )
                )

        saved_details.sort(key=lambda a: a.question_order)

        return AttemptResponse(
            id=attempt.id,
            assessment_version_id=attempt.assessment_version_id,
            version_number=version_number,
            status=attempt.status,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            total_questions=total_questions,
            answered_count=len(saved_details),
            answers=saved_details,
        )

    def _format_result_response(self, result: AssessmentResult) -> AssessmentResultResponse:
        suggestions = [
            CareerSuggestionItem(
                career_id=UUID(str(item["career_id"])),
                code=item["code"],
                title=item["title"],
                cluster=item["cluster"],
                overview=item["overview"],
                source_url=item["source_url"],
                similarity_score=float(item["similarity_score"]),
                reason=item["reason"],
            )
            for item in result.career_suggestions
        ]

        return AssessmentResultResponse(
            id=result.id,
            attempt_id=result.attempt_id,
            version=result.version,
            dimension_scores=result.dimension_scores,
            holland_code=result.holland_code,
            holland_code_label=result.holland_code_label,
            traits=result.traits,
            skills=result.skills,
            recommended_streams=result.recommended_streams,
            career_suggestions=suggestions,
            ai_explanation=result.ai_explanation,
            disclaimer_note=result.disclaimer_note,
            created_at=result.created_at,
        )

    async def ask_question(
        self,
        user: User,
        result_id: UUID,
        req: AssessmentQARequest,
    ) -> AssessmentQAResponse:
        result = await self.repo.get_result_by_id(result_id, user.id)
        if not result:
            raise AppException(
                status_code=404,
                code="RESULT_NOT_FOUND",
                message="Assessment result not found or access denied.",
            )

        clean_question = req.question.replace("<<<", "").replace(">>>", "").strip()

        suggested_careers = result.career_suggestions or []
        valid_career_ids = {str(s["career_id"]) for s in suggested_careers}
        catalog_lines = [
            f"- Career ID: {s['career_id']} | Title: {s['title']} | Cluster: {s['cluster']} | Overview: {s['overview']}"
            for s in suggested_careers
        ]
        career_catalog_str = "\n".join(catalog_lines)

        history_lines = [
            f"{m.role.capitalize()}: {m.content}"
            for m in req.conversation_history[-6:]
        ]
        conversation_history_str = "\n".join(history_lines) if history_lines else "No previous messages."

        def fallback_factory() -> AssessmentQAResponse:
            return AssessmentQAResponse(
                answer="I can only answer questions related to your career assessment results and suggested career paths.",
                referenced_career_ids=[],
                in_scope=False,
            )

        def post_validator(ai_data: AssessmentQAResponse) -> bool:
            if not ai_data.in_scope:
                return True
            for cid in ai_data.referenced_career_ids:
                if str(cid) not in valid_career_ids:
                    return False
            return True

        scores_str = "\n".join(f"- {dim}: {score:.1f}" for dim, score in sorted(result.dimension_scores.items()))

        gateway_resp = await self.gateway.execute_prompt(
            prompt_name="assessment_qa",
            prompt_version=1,
            schema=AssessmentQAResponse,
            fallback_factory=fallback_factory,
            system_variables={
                "holland_code": result.holland_code,
                "holland_code_label": result.holland_code_label or "",
                "dimension_scores": scores_str,
                "career_catalog": career_catalog_str,
                "conversation_history": conversation_history_str,
                "question": clean_question,
            },
            post_validator=post_validator,
        )

        resp_data = gateway_resp.data
        if not resp_data.in_scope:
            return fallback_factory()
        return resp_data

    async def choose_career(
        self,
        user: User,
        result_id: UUID,
        req: ChooseCareerRequest,
    ) -> ChooseCareerResponse:
        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)

        result = await self.repo.get_result_by_id(result_id, user.id)
        if not result:
            raise AppException(
                status_code=404,
                code="RESULT_NOT_FOUND",
                message="Assessment result not found or access denied.",
            )

        career = await self.career_repo.get_by_id(req.career_id, allow_drafts=allow_drafts)
        if not career:
            raise AppException(
                status_code=404,
                code="CAREER_NOT_FOUND",
                message="Target career not found or unverified.",
            )

        # Update profile if available
        if hasattr(self.session, "profile_repo"):
            prof_repo = getattr(self.session, "profile_repo")
            profile = await prof_repo.get_by_user_id(user.id)
            if profile:
                profile.preferred_career_id = career.id
                profile.target_career = career.title
                if hasattr(prof_repo, "save"):
                    await prof_repo.save(profile)

        return ChooseCareerResponse(
            message=f"Successfully chosen {career.title} as your target career.",
            career_id=career.id,
            career_title=career.title,
            result_id=result.id,
        )
