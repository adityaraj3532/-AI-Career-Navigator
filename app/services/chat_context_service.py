"""Context retrieval, data minimization, and prompt injection defense for AI Chat."""
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.career import Career
from app.models.interview import InterviewSession
from app.models.profile import StudentProfile
from app.models.progress import ActivityEvent
from app.models.roadmap import Roadmap, RoadmapItem
from app.models.skill import UserSkill
from app.services.planner_engine import compute_local_today
from app.services.progress_engine import current_streak

FIXED_FALLBACK_ANSWER = (
    "I can only provide guidance grounded in verified career data and your official learning roadmap. "
    "Please ask a question related to your career exploration, skills, roadmap milestones, or interview practice."
)

NO_ROADMAP_ANSWER = (
    "You don't have an active roadmap yet. To discuss and plan your personalized learning milestones, "
    "please create a roadmap first from the Roadmaps section."
)

TAG_STRIP_REGEX = re.compile(r"<\/?(user_query|context_data|system|assistant|instruction)[^>]*>", re.IGNORECASE)


def sanitize_untrusted_text(text_val: Optional[str], max_len: int = 1000) -> str:
    """Sanitize text by stripping delimiter tags and bounding length."""
    if not text_val:
        return ""
    clean = TAG_STRIP_REGEX.sub("", text_val)
    return clean.strip()[:max_len]


class ChatContextService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def build_context(
        self,
        user_id: UUID,
        mode: str,
        career_id: Optional[UUID] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, str]], bool]:
        """Build minimized context for the specified mode.

        Returns:
            (context_dict, retrieved_records_registry, can_proceed)
            If can_proceed is False (e.g. roadmap mode with no active roadmap),
            caller returns NO_ROADMAP_ANSWER immediately without calling AI.
        """
        # 1. Common student parameters (Strict data minimization: zero name/email/free-text)
        stmt_prof = select(StudentProfile).where(StudentProfile.user_id == user_id)
        res_prof = await self.session.execute(stmt_prof)
        profile = res_prof.scalar_one_or_none()

        user_tz = profile.timezone if (profile and profile.timezone) else "Asia/Kolkata"
        today = compute_local_today(user_tz)

        # Get active streak count
        stmt_events = (
            select(ActivityEvent.local_date)
            .where(ActivityEvent.user_id == user_id)
            .order_by(ActivityEvent.local_date.asc())
        )
        res_events = await self.session.execute(stmt_events)
        activity_dates = [d for d in res_events.scalars().all() if d is not None]
        streak_val = current_streak(activity_dates, today=today, allow_rest_day=True)

        student_common = {
            "hours_available_per_week": profile.hours_available_per_week if profile else None,
            "subjects_of_interest": profile.subjects_of_interest if profile else [],
            "current_streak_days": streak_val,
        }

        registry: Dict[str, Dict[str, str]] = {}
        mode_data: Dict[str, Any] = {}

        # 2. Mode-specific retrieval
        if mode == "career":
            if not career_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="career_id is required for 'career' mode.",
                )
            stmt_c = (
                select(Career)
                .where(Career.id == career_id)
                .options(
                    selectinload(Career.exams),
                    selectinload(Career.colleges),
                )
            )
            res_c = await self.session.execute(stmt_c)
            career = res_c.scalar_one_or_none()

            # Career must exist and be verified
            if not career or career.status != "verified":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Verified career '{career_id}' not found.",
                )

            cid_str = str(career.id)
            registry[cid_str] = {"type": "career", "title": career.title}

            exams_list = []
            for ex in (career.exams or []):
                eid_str = str(ex.id)
                registry[eid_str] = {"type": "exam", "title": ex.name}
                exams_list.append({"id": eid_str, "name": ex.name, "exam_type": ex.exam_type})

            colleges_list = []
            for col in (career.colleges or []):
                clid_str = str(col.id)
                registry[clid_str] = {"type": "college", "title": col.name}
                colleges_list.append({"id": clid_str, "name": col.name, "city": col.city})

            mode_data = {
                "career_id": cid_str,
                "title": career.title,
                "cluster": career.cluster,
                "overview": sanitize_untrusted_text(career.overview, max_len=600),
                "salary_range": career.salary_ranges,
                "exams": exams_list,
                "colleges": colleges_list,
            }

        elif mode == "roadmap":
            stmt_rm = (
                select(Roadmap)
                .where(Roadmap.user_id == user_id, Roadmap.status == "active")
                .options(
                    selectinload(Roadmap.phases),
                    selectinload(Roadmap.items),
                )
                .order_by(Roadmap.created_at.desc())
            )
            res_rm = await self.session.execute(stmt_rm)
            active_rm = res_rm.scalars().first()

            if not active_rm or not active_rm.phases:
                # User has no active roadmap: return can_proceed = False
                return {}, {}, False

            rmid_str = str(active_rm.id)
            registry[rmid_str] = {"type": "roadmap", "title": active_rm.title}

            # Find active phase (first phase with uncompleted items)
            phases_sorted = sorted(active_rm.phases, key=lambda p: p.phase_order)
            active_phase = phases_sorted[0]
            items_by_phase: Dict[UUID, List[RoadmapItem]] = {}
            for it in (active_rm.items or []):
                if it.phase_id:
                    items_by_phase.setdefault(it.phase_id, []).append(it)

            for p in phases_sorted:
                p_items = items_by_phase.get(p.id, [])
                if any(it.status in ("todo", "in_progress") for it in p_items):
                    active_phase = p
                    break

            pid_str = str(active_phase.id)
            registry[pid_str] = {"type": "roadmap_phase", "title": active_phase.name}

            pending_items = []
            remaining_mins = 0
            for it in items_by_phase.get(active_phase.id, []):
                if it.status in ("todo", "in_progress"):
                    itid_str = str(it.id)
                    registry[itid_str] = {"type": "roadmap_item", "title": it.title}
                    est_m = it.estimated_minutes or 30
                    remaining_mins += est_m
                    pending_items.append({
                        "id": itid_str,
                        "title": sanitize_untrusted_text(it.title, max_len=120),
                        "type": it.type,
                        "status": it.status,
                        "estimated_minutes": est_m,
                    })

            mode_data = {
                "roadmap_id": rmid_str,
                "title": active_rm.title,
                "current_phase": {
                    "id": pid_str,
                    "phase_order": active_phase.phase_order,
                    "name": active_phase.name,
                },
                "pending_items": pending_items[:10],
                "remaining_minutes_in_phase": remaining_mins,
            }

        elif mode == "skills":
            stmt_sk = select(UserSkill).where(UserSkill.user_id == user_id).order_by(UserSkill.updated_at.desc())
            res_sk = await self.session.execute(stmt_sk)
            skills = res_sk.scalars().all()

            user_skills_list = []
            for us in skills:
                usid_str = str(us.id)
                registry[usid_str] = {"type": "user_skill", "title": us.skill_name}
                user_skills_list.append({
                    "id": usid_str,
                    "skill_name": us.skill_name,
                    "current_level": us.level,
                    "is_verified": us.level_verified,
                    "verified_level": us.verified_level,
                    "tested_score_percentage": us.tested_score_percentage,
                })

            mode_data = {
                "tracked_skills": user_skills_list[:12],
            }

        elif mode == "interview":
            stmt_iv = (
                select(InterviewSession)
                .where(InterviewSession.user_id == user_id)
                .options(selectinload(InterviewSession.session_questions))
                .order_by(InterviewSession.started_at.desc())
                .limit(3)
            )
            res_iv = await self.session.execute(stmt_iv)
            sessions = res_iv.scalars().all()

            session_list = []
            for s in sessions:
                sid_str = str(s.id)
                registry[sid_str] = {"type": "interview_session", "title": f"{s.type.capitalize()} Interview ({s.level})"}

                # Gather key point evaluation labels (NEVER raw answer text!)
                questions_data = []
                for sq in (s.session_questions or []):
                    sqid_str = str(sq.id)
                    order_num = getattr(sq, "order", 1)
                    registry[sqid_str] = {"type": "interview_question", "title": f"Question {order_num}"}
                    # Covered key points
                    covered = []
                    if sq.results:
                        for r in sq.results:
                            covered.extend(r.covered_points or [])

                    questions_data.append({
                        "id": sqid_str,
                        "question_order": order_num,
                        "covered_key_points": covered,
                    })

                session_list.append({
                    "id": sid_str,
                    "type": s.type,
                    "level": s.level,
                    "status": s.status,
                    "questions": questions_data,
                })

            mode_data = {
                "recent_interview_sessions": session_list,
            }

        context_dict = {
            "mode": mode,
            "student_summary": student_common,
            "mode_data": mode_data,
        }
        return context_dict, registry, True


def validate_citations_and_build_sources(
    used_record_ids: List[str],
    registry: Dict[str, Dict[str, str]],
) -> Tuple[bool, List[Dict[str, str]]]:
    """Validate that used_record_ids is a strict subset of registry.

    If any unknown ID appears, returns (False, []).
    Otherwise returns (True, list of {record_id, type, title}).
    """
    valid_ids: Set[str] = set(registry.keys())
    sources: List[Dict[str, str]] = []

    for rid in used_record_ids:
        if rid not in valid_ids:
            return False, []
        meta = registry[rid]
        sources.append({
            "record_id": rid,
            "type": meta["type"],
            "title": meta["title"],
        })

    return True, sources
