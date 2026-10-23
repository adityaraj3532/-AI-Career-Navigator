from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.career import Career
from app.models.profile import StudentProfile
from app.models.roadmap import (
    ReplanHistory,
    Roadmap,
    RoadmapItem,
    RoadmapPhase,
)
from app.models.skill import SkillEvidence
from app.models.user import User
from app.repositories.career_repository import CareerRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.roadmap_repository import RoadmapRepository
from app.repositories.skill_repository import SkillRepository
from app.services.activity_service import record_activity
from app.schemas.roadmap import (
    CreateRoadmapRequest,
    ReplanResponse,
    ReplanRoadmapRequest,
    RoadmapDetailResponse,
    RoadmapItemResponse,
    RoadmapPhaseResponse,
    UpdateRoadmapItemRequest,
)
from app.services.roadmap_engine import (
    replan_roadmap_schedule,
    schedule_roadmap_items,
    validate_status_transition,
)
from app.services.skill_tracker_engine import compute_skill_level_and_confidence


class RoadmapService:
    MAX_ACTIVE_ROADMAPS = 3
    MAX_REPLANS_PER_WEEK = 3

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        if hasattr(session, "roadmap_repo"):
            self.repo = getattr(session, "roadmap_repo")
        else:
            self.repo = RoadmapRepository(session)

        if hasattr(session, "career_repo"):
            self.career_repo = getattr(session, "career_repo")
        else:
            self.career_repo = CareerRepository(session)

        if hasattr(session, "profile_repo"):
            self.profile_repo = getattr(session, "profile_repo")
        else:
            self.profile_repo = ProfileRepository(session)

        if hasattr(session, "skill_repo"):
            self.skill_repo = getattr(session, "skill_repo")
        else:
            self.skill_repo = SkillRepository(session)

    async def create_roadmap(
        self,
        user: User,
        req: CreateRoadmapRequest,
    ) -> RoadmapDetailResponse:
        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development") and getattr(settings, "ALLOW_DRAFT_ROADMAPS", False)

        # 1. Career existence and verification check
        career: Optional[Career] = await self.career_repo.get_by_id(req.career_id, allow_drafts=allow_drafts)
        if not career:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target career not found or unverified.",
            )

        # 2. Duplicate active roadmap check
        existing_active = await self.repo.get_active_roadmap_for_user_and_career(user.id, career.id)
        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active roadmap for this career.",
            )

        # 3. Maximum active roadmaps check
        active_count = await self.repo.count_user_active_roadmaps(user.id)
        if active_count >= self.MAX_ACTIVE_ROADMAPS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum limit of {self.MAX_ACTIVE_ROADMAPS} active roadmaps reached.",
            )

        # 4. Resolve weekly capacity
        profile: Optional[StudentProfile] = await self.profile_repo.get_by_user_id(user.id)
        hours = req.hours_per_week
        if hours is None:
            hours = float(profile.hours_available_per_week) if profile and profile.hours_available_per_week else 15.0

        # 5. Fetch verified template
        template = await self.repo.get_verified_template(career.id, allow_drafts=allow_drafts)
        if not template or not template.items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No verified roadmap template available for this career.",
            )

        # 6. Fetch tested skill levels for downweighting beginner items
        user_skills = await self.skill_repo.get_user_skills(user.id)
        tested_skill_levels: Dict[str, float] = {}
        for us in user_skills:
            if us.skill and us.confidence in ("medium", "high"):
                slug = us.skill.slug
                lvl_val = 3.0 if us.current_level == "advanced" else (2.0 if us.current_level == "intermediate" else 1.0)
                tested_skill_levels[slug] = lvl_val
                tested_skill_levels[str(us.skill_id)] = lvl_val

        # 7. Convert template items to dicts and run scheduling engine
        candidate_items = []
        for it in template.items:
            candidate_items.append({
                "template_item_id": it.id,
                "phase_id": it.phase_id,
                "item_code": it.item_code,
                "type": it.type,
                "title": it.title,
                "source_url": it.source_url,
                "estimated_minutes": it.estimated_minutes,
                "difficulty": it.difficulty,
                "topic": it.topic,
                "skill_id": it.skill_id,
                "prerequisites": it.prerequisites or [],
                "optional": it.optional,
                "status": "todo",
                "sequence_order": it.sequence_order,
                "extra_data": it.extra_data or {},
            })

        start_dt = req.start_date or datetime.now(timezone.utc)
        schedule_result = schedule_roadmap_items(
            items=candidate_items,
            hours_per_week=hours,
            start_date=start_dt,
            timezone_str=req.timezone or "Asia/Kolkata",
            tested_skill_levels=tested_skill_levels,
        )

        # 8. Clone Roadmap, Phases, and Items as independent user copies
        roadmap_id = uuid4()
        now = datetime.now(timezone.utc)
        total_weeks = schedule_result["total_weeks"]
        target_completion = start_dt + timedelta(weeks=total_weeks) if total_weeks > 0 else None

        roadmap = Roadmap(
            id=roadmap_id,
            user_id=user.id,
            career_id=career.id,
            template_id=template.id,
            template_version=template.version,
            title=f"{career.title} Roadmap",
            status="active",
            timezone=req.timezone or "Asia/Kolkata",
            hours_per_week=hours,
            start_date=start_dt,
            target_completion_date=target_completion,
            created_at=now,
            updated_at=now,
        )
        roadmap.career = career

        # Phase cloning
        phase_map: Dict[UUID, RoadmapPhase] = {}
        cloned_phases: List[RoadmapPhase] = []
        for p in template.phases:
            rp_id = uuid4()
            rp = RoadmapPhase(
                id=rp_id,
                roadmap_id=roadmap_id,
                name=p.name,
                phase_order=p.phase_order,
                description=p.description,
                created_at=now,
            )
            phase_map[p.id] = rp
            cloned_phases.append(rp)

        # Item cloning
        cloned_items: List[RoadmapItem] = []
        all_scheduled_and_backlog = schedule_result["scheduled_items"] + schedule_result["backlog_items"]
        for idx, it in enumerate(all_scheduled_and_backlog):
            t_phase_id = it.get("phase_id")
            new_phase = phase_map.get(t_phase_id)
            ri = RoadmapItem(
                id=uuid4(),
                roadmap_id=roadmap_id,
                phase_id=new_phase.id if new_phase else None,
                item_code=it.get("item_code"),
                type=it.get("type", "video"),
                title=it["title"],
                source_url=it.get("source_url"),
                estimated_minutes=it.get("estimated_minutes", 60),
                difficulty=it.get("difficulty", 1),
                topic=it.get("topic", "General"),
                skill_id=it.get("skill_id"),
                prerequisites=it.get("prerequisites", []),
                optional=it.get("optional", False),
                status="todo",
                scheduled_week=it.get("scheduled_week"),
                scheduled_date=it.get("scheduled_date"),
                order_index=idx,
                extra_data=it.get("extra_data", {}),
                created_at=now,
                updated_at=now,
            )
            cloned_items.append(ri)

        created_roadmap = await self.repo.create_cloned_roadmap(roadmap, cloned_phases, cloned_items)
        created_roadmap.phases = cloned_phases
        created_roadmap.items = cloned_items
        return self._format_detail_response(created_roadmap)

    async def get_roadmap(
        self,
        user: User,
        roadmap_id: UUID,
    ) -> RoadmapDetailResponse:
        roadmap = await self.repo.get_roadmap_by_id(roadmap_id)
        if not roadmap or roadmap.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap not found.",
            )
        return self._format_detail_response(roadmap)

    async def update_roadmap_item(
        self,
        user: User,
        item_id: UUID,
        req: UpdateRoadmapItemRequest,
    ) -> RoadmapItemResponse:
        item = await self.repo.get_roadmap_item_by_id(item_id)
        if not item or not item.roadmap or item.roadmap.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap item not found.",
            )

        try:
            validate_status_transition(item.status, req.status, force_undo=req.force_undo)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        now = datetime.now(timezone.utc)
        item.status = req.status
        item.updated_at = now

        if req.status == "done":
            item.completed_at = now
            # Hook: Ingest low-weight roadmap evidence into Skill Tracker
            await self._record_roadmap_skill_evidence(user.id, item)
            # Hook: Record activity in ledger
            session = getattr(self.repo, "session", None)
            if session:
                await record_activity(
                    session,
                    user_id=user.id,
                    source_type="roadmap_item",
                    source_id=str(item.id),
                    occurred_at=now,
                )
        elif req.force_undo and req.status != "done":
            item.completed_at = None

        saved = await self.repo.save_roadmap_item(item)
        return RoadmapItemResponse(
            id=saved.id,
            roadmap_id=saved.roadmap_id,
            phase_id=saved.phase_id,
            item_code=saved.item_code,
            type=saved.type,
            title=saved.title,
            source_url=saved.source_url,
            estimated_minutes=saved.estimated_minutes,
            difficulty=saved.difficulty,
            topic=saved.topic,
            skill_id=saved.skill_id,
            optional=saved.optional,
            status=saved.status,
            scheduled_week=saved.scheduled_week,
            scheduled_date=saved.scheduled_date,
            completed_at=saved.completed_at,
            order_index=saved.order_index,
        )

    async def replan_roadmap(
        self,
        user: User,
        roadmap_id: UUID,
        req: ReplanRoadmapRequest,
    ) -> ReplanResponse:
        roadmap = await self.repo.get_roadmap_by_id(roadmap_id)
        if not roadmap or roadmap.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap not found.",
            )

        # Rate limit check on replans (max 3 times per week)
        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(days=7)
        recent_replans = [
            h for h in (roadmap.replan_history or [])
            if h.created_at >= one_week_ago
        ]
        if len(recent_replans) >= self.MAX_REPLANS_PER_WEEK:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Replan limit reached. You can replan up to 3 times per week.",
            )

        hours = req.hours_per_week or roadmap.hours_per_week
        replan_dt = req.replan_date or now

        # Convert items to dicts
        item_dicts = []
        for it in roadmap.items:
            item_dicts.append({
                "id": it.id,
                "item_code": it.item_code,
                "type": it.type,
                "title": it.title,
                "estimated_minutes": it.estimated_minutes,
                "difficulty": it.difficulty,
                "topic": it.topic,
                "skill_id": it.skill_id,
                "prerequisites": it.prerequisites or [],
                "optional": it.optional,
                "status": it.status,
                "scheduled_week": it.scheduled_week,
                "scheduled_date": it.scheduled_date,
            })

        replan_res = replan_roadmap_schedule(
            existing_items=item_dicts,
            replan_date=replan_dt,
            hours_per_week=hours,
            timezone_str=roadmap.timezone or "Asia/Kolkata",
        )

        # Update items in DB
        rescheduled_lookup = {it["id"]: it for it in replan_res["all_items"]}
        for it in roadmap.items:
            if it.id in rescheduled_lookup:
                updated_meta = rescheduled_lookup[it.id]
                it.scheduled_week = updated_meta.get("scheduled_week")
                it.scheduled_date = updated_meta.get("scheduled_date")
                await self.repo.save_roadmap_item(it)

        # Record replan history
        hist = ReplanHistory(
            id=uuid4(),
            roadmap_id=roadmap.id,
            reason="User requested pace readjustment",
            summary=replan_res["summary"],
            created_at=now,
        )
        await self.repo.save_replan_history(hist)

        return ReplanResponse(
            roadmap_id=roadmap.id,
            preserved_count=replan_res["preserved_count"],
            rescheduled_count=replan_res["rescheduled_count"],
            total_weeks=replan_res["total_weeks"],
            summary=replan_res["summary"],
        )

    async def _record_roadmap_skill_evidence(self, user_id: UUID, item: RoadmapItem) -> None:
        """Record low-weight evidence into Skill Tracker upon roadmap item completion."""
        skill = None
        if item.skill_id:
            skill = await self.skill_repo.get_skill_by_id(item.skill_id)
        elif item.topic:
            skill = await self.skill_repo.find_skill_by_name_or_alias(item.topic)

        if skill:
            existing = await self.skill_repo.get_evidence_by_source("roadmap", item.id)
            if existing:
                return

            ev = SkillEvidence(
                user_id=user_id,
                skill_id=skill.id,
                source_type="roadmap",
                source_id=item.id,
                score=75,
                level_signal="intermediate",
                subtopic_scores={},
                summary=f"Completed roadmap milestone: {item.title}",
            )
            await self.skill_repo.add_evidence(ev)

            all_ev = await self.skill_repo.get_skill_evidence_for_user(user_id, skill.id)
            ev_dicts = [
                {"source_type": e.source_type, "created_at": e.created_at, "level_signal": e.level_signal, "score": e.score}
                for e in all_ev
            ]
            calc_lvl, calc_conf, _ = compute_skill_level_and_confidence(ev_dicts)
            await self.skill_repo.upsert_user_skill(user_id, skill.id, calc_lvl, calc_conf)

    def _format_detail_response(self, roadmap: Roadmap) -> RoadmapDetailResponse:
        total_items = len(roadmap.items)
        completed_items = sum(1 for it in roadmap.items if it.status == "done")
        comp_pct = round((completed_items / total_items) * 100.0, 1) if total_items > 0 else 0.0

        scheduled_by_phase: Dict[Optional[UUID], List[RoadmapItemResponse]] = {}
        backlog: List[RoadmapItemResponse] = []

        for it in roadmap.items:
            resp_item = RoadmapItemResponse(
                id=it.id,
                roadmap_id=it.roadmap_id,
                phase_id=it.phase_id,
                item_code=it.item_code,
                type=it.type,
                title=it.title,
                source_url=it.source_url,
                estimated_minutes=it.estimated_minutes,
                difficulty=it.difficulty,
                topic=it.topic,
                skill_id=it.skill_id,
                optional=it.optional,
                status=it.status,
                scheduled_week=it.scheduled_week,
                scheduled_date=it.scheduled_date,
                completed_at=it.completed_at,
                order_index=it.order_index,
            )
            if it.scheduled_week is None:
                backlog.append(resp_item)
            else:
                scheduled_by_phase.setdefault(it.phase_id, []).append(resp_item)

        phase_responses: List[RoadmapPhaseResponse] = []
        for p in roadmap.phases:
            p_items = scheduled_by_phase.get(p.id, [])
            p_items.sort(key=lambda x: (x.scheduled_week or 999, x.order_index))
            phase_responses.append(
                RoadmapPhaseResponse(
                    id=p.id,
                    name=p.name,
                    phase_order=p.phase_order,
                    description=p.description,
                    items=p_items,
                )
            )
        phase_responses.sort(key=lambda x: x.phase_order)

        # Target entrances from career exams
        entrances = []
        if roadmap.career and getattr(roadmap.career, "exams", None):
            for e in roadmap.career.exams:
                entrances.append({
                    "id": str(e.id),
                    "code": e.code,
                    "name": e.name,
                    "exam_level": e.exam_level,
                    "source_url": e.source_url,
                })

        total_weeks = max([it.scheduled_week for it in roadmap.items if it.scheduled_week], default=0)

        return RoadmapDetailResponse(
            id=roadmap.id,
            user_id=roadmap.user_id,
            career_id=roadmap.career_id,
            career_title=roadmap.career.title if roadmap.career else "Career Roadmap",
            template_id=roadmap.template_id,
            template_version=roadmap.template_version,
            title=roadmap.title,
            status=roadmap.status,
            timezone=roadmap.timezone,
            hours_per_week=roadmap.hours_per_week,
            start_date=roadmap.start_date,
            target_completion_date=roadmap.target_completion_date,
            total_weeks=total_weeks,
            completion_percentage=comp_pct,
            total_items=total_items,
            completed_items=completed_items,
            phases=phase_responses,
            backlog_items=backlog,
            target_entrances=entrances,
        )
