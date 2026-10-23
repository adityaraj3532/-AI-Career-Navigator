import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.llm.gateway import LLMGateway
from app.models.skill import SkillEvidence
from app.repositories.interview_repository import (
    ActiveSessionExistsError,
    InsufficientQuestionsError,
    InterviewRepository,
)
from app.repositories.skill_repository import SkillRepository
from app.schemas.interview import (
    DimensionScores,
    DimensionTrend,
    InterviewAnalyticsResponse,
    InterviewHistoryItem,
    InterviewHistoryResponse,
    PublicSessionQuestion,
    QuestionFeedbackResponse,
    SessionDetailResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    TranscriptItem,
)
from app.services.interview_scoring_engine import (
    DEFAULT_RUBRIC_VERSION,
    compute_depth_signal,
    compute_scores_from_coverage,
    compute_structure_signal,
    fallback_score_answer,
)

logger = logging.getLogger(__name__)

# Anti-PII post-validator regex for AI follow-up questions
PII_REQUEST_PATTERN = re.compile(
    r"\b(phone number|mobile number|email address|password|social security|aadhaar|pan card|credit card|home address|personal identity)\b",
    re.IGNORECASE,
)


class InterviewEvaluationAIOutput(BaseModel):
    covered_points: Dict[str, bool] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)


class InterviewFollowUpAIOutput(BaseModel):
    follow_up_question: str = Field(default="")

PRACTICE_GUIDANCE_NOTE = "Feedback is practice guidance to support interview preparation."


class InterviewService:
    def __init__(
        self,
        repo: InterviewRepository,
        skill_repo: Optional[SkillRepository] = None,
        gateway: Optional[LLMGateway] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.repo = repo
        self.skill_repo = skill_repo
        self.gateway = gateway
        self.settings = settings or Settings()
        self._prompt_cache: Dict[str, str] = {}
        # In-memory per-user start counter for rate limiting (fallback when Redis is not bound)
        self._start_counts: Dict[UUID, List[datetime]] = {}

    def _get_prompt_template(self, prompt_filename: str) -> str:
        if prompt_filename not in self._prompt_cache:
            p = Path(__file__).resolve().parent.parent / "llm" / "prompts" / prompt_filename
            if p.is_file():
                self._prompt_cache[prompt_filename] = p.read_text(encoding="utf-8")
            else:
                self._prompt_cache[prompt_filename] = ""
        return self._prompt_cache[prompt_filename]

    def _check_start_rate_limit(self, user_id: UUID) -> None:
        """Enforces a per-user rate limit of at most 10 interview starts per hour."""
        now = datetime.now(timezone.utc)
        timestamps = self._start_counts.setdefault(user_id, [])
        # Keep timestamps from the last 3600 seconds
        valid = [t for t in timestamps if (now - t).total_seconds() < 3600]
        self._start_counts[user_id] = valid
        if len(valid) >= 10:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Interview start rate limit exceeded. Please wait before initiating another mock interview.",
            )
        self._start_counts[user_id].append(now)

    async def start_interview(
        self,
        user_id: UUID,
        req: StartInterviewRequest,
    ) -> StartInterviewResponse:
        """Starts a new mock interview session and returns the first question without criteria."""
        self._check_start_rate_limit(user_id)

        allow_drafts = (
            self.settings.ENVIRONMENT.lower() == "development"
            and getattr(self.settings, "ALLOW_DRAFT_QUESTIONS", False)
        )

        try:
            questions = await self.repo.get_questions_for_interview(
                career_id=req.career_id,
                type=req.type,
                level=req.level,
                limit=req.num_questions,
                allow_drafts=allow_drafts,
            )
        except InsufficientQuestionsError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        try:
            session = await self.repo.create_session(
                user_id=user_id,
                career_id=req.career_id,
                type=req.type,
                level=req.level,
                questions=questions,
            )
        except ActiveSessionExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

        first_sq = session.session_questions[0]
        return StartInterviewResponse(
            session_id=session.id,
            career_id=session.career_id,
            type=session.type,
            level=session.level,
            status=session.status,
            expires_at=session.expires_at,
            current_question=PublicSessionQuestion(
                id=first_sq.id,
                order=first_sq.order,
                question_text=first_sq.question_text,
                is_follow_up=first_sq.is_follow_up,
            ),
            total_questions=len(session.session_questions),
        )

    async def _evaluate_answer_with_ai(
        self,
        question_text: str,
        key_points: List[Dict[str, Any]],
        answer_text: str,
    ) -> Optional[Dict[str, Any]]:
        """Invokes LLMGateway to judge key point coverage booleans only.

        Code computes every number (depth, structure, overall composite).
        Never penalises grammar, spelling, or language choice.
        """
        if not self.gateway:
            return None

        kp_summary = [
            {"id": kp["id"], "text": kp["text"]} for kp in key_points
        ]
        valid_ids = {kp["id"] for kp in key_points}

        fallback_obj = InterviewEvaluationAIOutput(
            covered_points={kp["id"]: False for kp in key_points},
            strengths=[],
            improvements=[],
        )

        try:
            gw_res = await self.gateway.generate(
                prompt_name="interview_evaluation",
                inputs={
                    "question_text": question_text,
                    "key_points_json": json.dumps(kp_summary, indent=2),
                    "candidate_answer": answer_text,
                },
                output_schema=InterviewEvaluationAIOutput,
                fallback=fallback_obj,
                version=1,
            )

            if gw_res.telemetry.fallback_used:
                return None

            data = gw_res.data
            if not any(k in valid_ids for k in data.covered_points):
                logger.info("AI evaluation returned no recognized key points; activating fallback scorer.")
                return None

            bool_map = {
                k: bool(v) for k, v in data.covered_points.items() if k in valid_ids
            }
            # Fill missing with False
            for kpid in valid_ids:
                bool_map.setdefault(kpid, False)

            # Invariant: Code computes every number (depth and structure signals)
            depth_sig = compute_depth_signal(answer_text)
            struct_sig = compute_structure_signal(answer_text)

            return {
                "covered_points_map": bool_map,
                "depth_signal": depth_sig,
                "structure_signal": struct_sig,
                "strengths": [str(s)[:200] for s in data.strengths[:3]],
                "improvements": [str(i)[:200] for i in data.improvements[:3]],
            }
        except Exception as e:
            logger.warning(f"AI interview evaluation failed or timed out: {e}")
            return None

    async def _generate_follow_up_question(
        self,
        question_text: str,
        missing_points: List[str],
        answer_text: str,
    ) -> Optional[str]:
        """Generates a targeted, on-topic follow-up question via LLMGateway."""
        if not self.gateway:
            return None

        fallback_obj = InterviewFollowUpAIOutput(follow_up_question="")

        try:
            gw_res = await self.gateway.generate(
                prompt_name="interview_followup",
                inputs={
                    "question_text": question_text,
                    "missing_points": ", ".join(missing_points),
                    "candidate_answer": answer_text,
                },
                output_schema=InterviewFollowUpAIOutput,
                fallback=fallback_obj,
                version=1,
            )

            if gw_res.telemetry.fallback_used:
                return None

            q_text = gw_res.data.follow_up_question.strip()
            if not q_text or len(q_text) > 250:
                return None

            # Post-validator: Reject any question requesting personal details
            if PII_REQUEST_PATTERN.search(q_text):
                logger.warning("Rejected AI follow-up containing personal detail inquiry.")
                return None

            return q_text
        except Exception:
            return None
            return None

    async def submit_answer(
        self,
        user_id: UUID,
        session_id: UUID,
        req: SubmitAnswerRequest,
    ) -> QuestionFeedbackResponse:
        """Submits candidate answer, executes scoring, generates feedback and sample answers."""
        session = await self.repo.get_session_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{session_id}' not found.",
            )

        now = datetime.now(timezone.utc)
        if session.status != "in_progress" or session.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview session is no longer active or has expired.",
            )

        # Find target question in session
        target_sq = next((sq for sq in session.session_questions if sq.id == req.session_question_id), None)
        if not target_sq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question '{req.session_question_id}' does not belong to this interview session.",
            )

        if getattr(target_sq, "answer", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This question has already been answered.",
            )

        # Invariant: NEVER log answer text for candidate privacy
        await self.repo.save_answer(
            session_question_id=target_sq.id,
            user_id=user_id,
            answer_text=req.answer_text,
        )

        # 1. Scoring & Key-Point Judging
        ai_eval = await self._evaluate_answer_with_ai(
            question_text=target_sq.question_text,
            key_points=target_sq.key_points,
            answer_text=req.answer_text,
        )

        if ai_eval:
            scores = compute_scores_from_coverage(
                key_points=target_sq.key_points,
                covered_points_map=ai_eval["covered_points_map"],
                depth_signal=ai_eval["depth_signal"],
                structure_signal=ai_eval["structure_signal"],
                rubric_version=DEFAULT_RUBRIC_VERSION,
            )
            scoring_method = "ai"
            confidence = "high"
            strengths = ai_eval["strengths"]
            improvements = ai_eval["improvements"]
        else:
            fallback = fallback_score_answer(
                key_points=target_sq.key_points,
                answer_text=req.answer_text,
                rubric_version=DEFAULT_RUBRIC_VERSION,
            )
            scores = fallback.scores
            scoring_method = "fallback"
            confidence = "low"
            # Deterministic constructive feedback phrasing
            covered_set = set(scores.covered_points)
            strengths = [
                f"Addressed: {kp['text']}" for kp in target_sq.key_points if kp["id"] in covered_set
            ][:3]
            improvements = [
                f"Consider explaining: {kp['text']}" for kp in target_sq.key_points if kp["id"] not in covered_set
            ][:3]

        await self.repo.save_result(
            session_id=session.id,
            session_question_id=target_sq.id,
            rubric_version=DEFAULT_RUBRIC_VERSION,
            scores=scores,
            scoring_method=scoring_method,
            confidence=confidence,
        )

        # 2. Dynamic Follow-Up Determination
        next_q: Optional[PublicSessionQuestion] = None
        uncovered = [
            kp["text"] for kp in target_sq.key_points if kp["id"] not in scores.covered_points
        ]

        # Trigger follow-up if depth is low (< 50) or key points missed, question is not a follow-up, and session length < 5
        has_follow_up_child = any(sq.parent_session_question_id == target_sq.id for sq in session.session_questions)
        if (
            (scores.depth_score < 50 or uncovered)
            and not target_sq.is_follow_up
            and not has_follow_up_child
            and len(session.session_questions) < 5
        ):
            follow_up_text = await self._generate_follow_up_question(
                question_text=target_sq.question_text,
                missing_points=uncovered or ["practical trade-offs"],
                answer_text=req.answer_text,
            )
            if follow_up_text:
                new_sq = await self.repo.add_follow_up_question(
                    session_id=session.id,
                    parent_id=target_sq.id,
                    order=len(session.session_questions) + 1,
                    question_text=follow_up_text,
                    key_points=target_sq.key_points,
                )
                session.session_questions.append(new_sq)
                next_q = PublicSessionQuestion(
                    id=new_sq.id,
                    order=new_sq.order,
                    question_text=new_sq.question_text,
                    is_follow_up=True,
                )

        # If no follow-up generated, find next unanswered question
        if not next_q:
            # Re-fetch session questions
            answered_ids = {
                sq.id for sq in session.session_questions if getattr(sq, "answer", None) or sq.id == target_sq.id
            }
            unanswered = [sq for sq in session.session_questions if sq.id not in answered_ids]
            if unanswered:
                unanswered.sort(key=lambda x: x.order)
                nq = unanswered[0]
                next_q = PublicSessionQuestion(
                    id=nq.id,
                    order=nq.order,
                    question_text=nq.question_text,
                    is_follow_up=nq.is_follow_up,
                )

        session_completed = next_q is None

        # 3. Finalize Session Completion & Skill Evidence
        if session_completed:
            session.status = "completed"
            session.completed_at = now
            # Aggregate all results for session
            session_obj = await self.repo.get_session_by_id(session.id)
            if session_obj:
                all_res = []
                for sq in session_obj.session_questions:
                    all_res.extend(sq.results or [])
                if all_res:
                    cov_avg = int(round(sum(r.coverage_score for r in all_res) / len(all_res)))
                    dep_avg = int(round(sum(r.depth_score for r in all_res) / len(all_res)))
                    str_avg = int(round(sum(r.structure_score for r in all_res) / len(all_res)))
                    ovr_avg = int(round(sum(r.overall_score for r in all_res) / len(all_res)))
                    # Overall session result
                    await self.repo.save_result(
                        session_id=session.id,
                        session_question_id=None,
                        rubric_version=DEFAULT_RUBRIC_VERSION,
                        scores=DimensionScores(
                            coverage_score=cov_avg,
                            depth_score=dep_avg,
                            structure_score=str_avg,
                            overall_score=ovr_avg,
                            covered_points=[],
                            rubric_version=DEFAULT_RUBRIC_VERSION,
                        ),
                        scoring_method=scoring_method,
                        confidence=confidence,
                    )
                    # Skill tracker hook (idempotent evidence recording)
                    if self.skill_repo and session.career_id:
                        await self._record_skill_evidence(user_id, session.id, session.career_id, ovr_avg)

                    # Ledger activity hook
                    session_db = getattr(self.repo, "session", None)
                    if session_db:
                        from app.services.activity_service import record_activity
                        await record_activity(
                            session_db,
                            user_id=user_id,
                            source_type="interview_session",
                            source_id=str(session.id),
                            occurred_at=now,
                        )

            await self.repo.update_session(session)

        # Retrieve sample answer now that candidate has submitted
        sample_answer = None
        if target_sq.question_id:
            q_row = await self.repo.get_question_by_id(target_sq.question_id)
            if q_row:
                sample_answer = q_row.sample_answer

        return QuestionFeedbackResponse(
            session_question_id=target_sq.id,
            scores=scores,
            covered_points=scores.covered_points,
            scoring_method=scoring_method,
            confidence=confidence,
            strengths=strengths,
            improvements=improvements,
            sample_answer=sample_answer,
            next_question=next_q,
            session_completed=session_completed,
            practice_guidance_note=PRACTICE_GUIDANCE_NOTE,
        )

    async def _record_skill_evidence(
        self,
        user_id: UUID,
        session_id: UUID,
        career_id: UUID,
        overall_score: int,
    ) -> None:
        """Idempotently records low-weight interview practice evidence into SkillEvidence."""
        if not self.skill_repo:
            return

        existing = await self.skill_repo.get_evidence_by_source("interview", session_id)
        if existing:
            return

        # Find primary skill for career or general engineering skill
        user_skills = await self.skill_repo.get_user_skills(user_id)
        skill_id = user_skills[0].skill_id if user_skills else None
        if not skill_id:
            return

        evidence = SkillEvidence(
            user_id=user_id,
            skill_id=skill_id,
            source_type="interview",
            source_id=session_id,
            score=overall_score,
            level_signal="intermediate" if overall_score >= 65 else "beginner",
            subtopic_scores={"mock_interview_overall": overall_score},
            summary="Completed career mock interview session with rubric evaluation.",
        )
        await self.skill_repo.add_evidence(evidence)

    async def get_session_detail(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> SessionDetailResponse:
        """Returns full session transcript and rubric breakdown for session owner only."""
        session = await self.repo.get_session_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{session_id}' not found.",
            )

        items: List[TranscriptItem] = []
        overall_res = await self.repo.get_session_overall_result(session.id)

        for sq in session.session_questions:
            ans = getattr(sq, "answer", None)
            res_item = sq.results[0] if getattr(sq, "results", None) else None

            sample_ans = None
            if ans and sq.question_id:
                # Safe to reveal sample answer for answered questions
                q_row = await self.repo.get_question_by_id(sq.question_id)
                if q_row:
                    sample_ans = q_row.sample_answer

            scores_obj = None
            covered_list = []
            if res_item:
                scores_obj = DimensionScores(
                    coverage_score=res_item.coverage_score,
                    depth_score=res_item.depth_score,
                    structure_score=res_item.structure_score,
                    overall_score=res_item.overall_score,
                    covered_points=res_item.covered_points or [],
                    rubric_version=res_item.rubric_version,
                )
                covered_list = res_item.covered_points or []

            items.append(
                TranscriptItem(
                    session_question_id=sq.id,
                    order=sq.order,
                    question_text=sq.question_text,
                    is_follow_up=sq.is_follow_up,
                    answer_text=ans.answer_text if ans else None,
                    submitted_at=ans.submitted_at if ans else None,
                    scores=scores_obj,
                    covered_points=covered_list,
                    strengths=[],
                    improvements=[],
                    sample_answer=sample_ans,
                )
            )

        return SessionDetailResponse(
            session_id=session.id,
            career_id=session.career_id,
            type=session.type,
            level=session.level,
            status=session.status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            completed_at=session.completed_at,
            overall_score=overall_res.overall_score if overall_res else None,
            coverage_score=overall_res.coverage_score if overall_res else None,
            depth_score=overall_res.depth_score if overall_res else None,
            structure_score=overall_res.structure_score if overall_res else None,
            questions=items,
            practice_guidance_note=PRACTICE_GUIDANCE_NOTE,
        )

    async def get_history(
        self,
        user_id: UUID,
        type: Optional[str] = None,
        career_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> InterviewHistoryResponse:
        """Returns paginated history of completed interview sessions."""
        sessions, total = await self.repo.get_completed_sessions_for_user(
            user_id=user_id,
            type=type,
            career_id=career_id,
            page=page,
            page_size=page_size,
        )

        history_items = []
        for s in sessions:
            r = await self.repo.get_session_overall_result(s.id)

            history_items.append(
                InterviewHistoryItem(
                    session_id=s.id,
                    career_id=s.career_id,
                    type=s.type,
                    level=s.level,
                    status=s.status,
                    started_at=s.started_at,
                    completed_at=s.completed_at,
                    overall_score=r.overall_score if r else None,
                    coverage_score=r.coverage_score if r else None,
                    depth_score=r.depth_score if r else None,
                    structure_score=r.structure_score if r else None,
                )
            )

        return InterviewHistoryResponse(
            items=history_items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_analytics(
        self,
        user_id: UUID,
        type: Optional[str] = None,
    ) -> InterviewAnalyticsResponse:
        """Calculates progression trends across dimensions.

        Returns null trends if fewer than 2 comparable sessions exist.
        """
        completed = await self.repo.get_completed_sessions_for_analytics(user_id=user_id, type=type)

        # Filter sessions with valid overall results
        comparable_data = []
        for s in completed:
            r = await self.repo.get_session_overall_result(s.id)
            if r and r.rubric_version == DEFAULT_RUBRIC_VERSION:
                comparable_data.append((s, r))

        if len(comparable_data) < 2:
            return InterviewAnalyticsResponse(
                has_sufficient_data=False,
                total_completed=len(comparable_data),
                message="At least 2 completed sessions of the same interview type and rubric version are required to calculate improvement trends.",
                trends=None,
                weakest_dimension=None,
                strongest_dimension=None,
            )

        # Calculate progression lists
        cov_prog = [r.coverage_score for _, r in comparable_data]
        dep_prog = [r.depth_score for _, r in comparable_data]
        str_prog = [r.structure_score for _, r in comparable_data]
        ovr_prog = [r.overall_score for _, r in comparable_data]

        def make_trend(name: str, values: List[int]) -> DimensionTrend:
            avg = round(sum(values) / len(values), 1)
            pct_change = round(((values[-1] - values[0]) / max(1, values[0])) * 100.0, 1) if values[0] > 0 else 0.0
            return DimensionTrend(
                dimension=name,
                average_score=avg,
                change_pct=pct_change,
                progression=values,
            )

        trends_map = {
            "coverage": make_trend("coverage", cov_prog),
            "depth": make_trend("depth", dep_prog),
            "structure": make_trend("structure", str_prog),
            "overall": make_trend("overall", ovr_prog),
        }

        dim_averages = {
            "coverage": trends_map["coverage"].average_score,
            "depth": trends_map["depth"].average_score,
            "structure": trends_map["structure"].average_score,
        }
        strongest = max(dim_averages, key=dim_averages.get)
        weakest = min(dim_averages, key=dim_averages.get)

        return InterviewAnalyticsResponse(
            has_sufficient_data=True,
            total_completed=len(comparable_data),
            trends=trends_map,
            weakest_dimension=weakest,
            strongest_dimension=strongest,
        )
