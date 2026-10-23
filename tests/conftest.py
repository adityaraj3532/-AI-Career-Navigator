import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.llm.gateway import LLMGateway
from app.llm.provider import MockLLMProvider
from app.main import app
from app.models.assessment import (
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentResult,
    AssessmentVersion,
)
from app.models.auth import RefreshToken
from app.models.profile import StudentProfile
from app.models.adaptive_test import (
    TestQuestionBank,
    TestAttempt,
    TestAttemptAnswer,
)
from app.models.career import (
    Career,
    Certificate,
    College,
    Course,
    Exam,
    Internship,
    UserShortlist,
    UserCareerCompatibilitySnapshot,
)
from app.models.skill import (
    Skill,
    SkillEvidence,
    UserSkill,
)
from app.models.exam_cycle import ExamCycle
from app.models.roadmap import (
    RoadmapTemplate,
    TemplatePhase,
    TemplateItem,
)
from app.models.user import User
from app.schemas.assessment import AnswerItem


class InMemoryUserRepo:
    def __init__(self, users_dict: Dict[UUID, User]) -> None:
        self.users = users_dict

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        clean_email = email.strip().lower()
        for u in self.users.values():
            if u.email.strip().lower() == clean_email:
                return u
        return None

    async def create(self, user: User) -> User:
        if not user.id:
            user.id = uuid4()
        user.created_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        self.users[user.id] = user
        return user

    async def update_password(self, user_id: UUID, hashed_password: str) -> None:
        if user_id in self.users:
            self.users[user_id].hashed_password = hashed_password
            self.users[user_id].updated_at = datetime.now(timezone.utc)


class InMemoryTokenRepo:
    def __init__(self, tokens_dict: Dict[UUID, RefreshToken]) -> None:
        self.tokens = tokens_dict

    async def create_refresh_token(
        self,
        user_id: UUID,
        family_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token_id = uuid4()
        rec = RefreshToken(
            id=token_id,
            user_id=user_id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
            used_at=None,
            revoked_at=None,
        )
        self.tokens[token_id] = rec
        return rec

    async def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        for t in self.tokens.values():
            if t.token_hash == token_hash:
                return t
        return None

    async def mark_token_used(self, token_id: UUID) -> None:
        if token_id in self.tokens:
            self.tokens[token_id].used_at = datetime.now(timezone.utc)

    async def revoke_family(self, family_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        for t in self.tokens.values():
            if t.family_id == family_id and t.revoked_at is None:
                t.revoked_at = now

    async def revoke_user_tokens(self, user_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        for t in self.tokens.values():
            if t.user_id == user_id and t.revoked_at is None:
                t.revoked_at = now

    async def delete_expired_tokens(self) -> int:
        now = datetime.now(timezone.utc)
        expired_ids = [tid for tid, t in self.tokens.items() if t.expires_at < now]
        for tid in expired_ids:
            del self.tokens[tid]
        return len(expired_ids)


class InMemoryCareerRepo:
    def __init__(self, careers_dict: Dict[UUID, Career]) -> None:
        self.careers = careers_dict

    async def get_careers(self, allow_drafts: bool = False) -> List[Career]:
        res = []
        for c in self.careers.values():
            if allow_drafts or c.status == "verified":
                res.append(c)
        res.sort(key=lambda x: (x.title, str(x.id)))
        return res

    async def list_careers(
        self,
        cluster: Optional[str] = None,
        demand: Optional[str] = None,
        min_salary: Optional[int] = None,
        max_salary: Optional[int] = None,
        allow_drafts: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Career], int]:
        res = []
        for c in self.careers.values():
            if not allow_drafts and c.status != "verified":
                continue
            if cluster and c.cluster != cluster:
                continue
            if demand and c.demand != demand:
                continue
            if min_salary is not None:
                entry_min = c.salary_ranges.get("entry", {}).get("min", 0) if c.salary_ranges else 0
                mid_min = c.salary_ranges.get("mid", {}).get("min", 0) if c.salary_ranges else 0
                if entry_min < min_salary and mid_min < min_salary:
                    continue
            if max_salary is not None:
                entry_max = c.salary_ranges.get("entry", {}).get("max", 0) if c.salary_ranges else 0
                mid_max = c.salary_ranges.get("mid", {}).get("max", 0) if c.salary_ranges else 0
                if entry_max > max_salary and mid_max > max_salary:
                    continue
            res.append(c)

        res.sort(key=lambda x: (x.title, str(x.id)))
        total_count = len(res)
        offset = (page - 1) * page_size
        return res[offset : offset + page_size], total_count

    async def get_by_id(
        self,
        career_id: UUID,
        allow_drafts: bool = False,
        eager_load: bool = True,
    ) -> Optional[Career]:
        c = self.careers.get(career_id)
        if not c:
            return None
        if not allow_drafts and c.status != "verified":
            return None
        return c

    async def get_by_code(self, code: str, allow_drafts: bool = False) -> Optional[Career]:
        for c in self.careers.values():
            if c.code == code:
                if not allow_drafts and c.status != "verified":
                    return None
                return c
        return None


class InMemoryAssessmentRepo:
    def __init__(self, storage: Dict[str, Any]) -> None:
        self.versions: Dict[UUID, AssessmentVersion] = storage["versions"]
        self.questions: Dict[UUID, AssessmentQuestion] = storage["questions"]
        self.attempts: Dict[UUID, AssessmentAttempt] = storage["attempts"]
        self.answers: Dict[UUID, AssessmentAnswer] = storage["answers"]
        self.results: Dict[UUID, AssessmentResult] = storage.setdefault("results", {})

    async def get_active_version(self) -> Optional[AssessmentVersion]:
        for v in self.versions.values():
            if v.is_active:
                v.questions = [q for q in self.questions.values() if q.assessment_version_id == v.id]
                v.questions.sort(key=lambda x: x.question_order)
                return v
        return None

    async def get_version_by_id(self, version_id: UUID) -> Optional[AssessmentVersion]:
        return self.versions.get(version_id)

    async def get_questions_for_version(self, version_id: UUID) -> List[AssessmentQuestion]:
        qs = [q for q in self.questions.values() if q.assessment_version_id == version_id and q.is_active]
        qs.sort(key=lambda x: x.question_order)
        return qs

    async def get_active_draft_attempt(self, user_id: UUID) -> Optional[AssessmentAttempt]:
        for att in self.attempts.values():
            if att.user_id == user_id and att.status == "draft":
                self._populate_attempt(att)
                return att
        return None

    async def get_attempt_by_id(self, attempt_id: UUID, user_id: UUID) -> Optional[AssessmentAttempt]:
        att = self.attempts.get(attempt_id)
        if att and att.user_id == user_id:
            self._populate_attempt(att)
            return att
        return None

    def _populate_attempt(self, att: AssessmentAttempt) -> None:
        att.assessment_version = self.versions.get(att.assessment_version_id)
        att.answers = [a for a in self.answers.values() if a.attempt_id == att.id]
        for a in att.answers:
            a.question = self.questions.get(a.question_id)

    async def create_attempt(self, user_id: UUID, version_id: UUID) -> AssessmentAttempt:
        attempt_id = uuid4()
        now = datetime.now(timezone.utc)
        att = AssessmentAttempt(
            id=attempt_id,
            user_id=user_id,
            assessment_version_id=version_id,
            status="draft",
            started_at=now,
            updated_at=now,
            submitted_at=None,
        )
        self.attempts[attempt_id] = att
        self._populate_attempt(att)
        return att

    async def upsert_answers(self, attempt_id: UUID, answers: List[AnswerItem]) -> None:
        now = datetime.now(timezone.utc)
        for item in answers:
            found = False
            for a in self.answers.values():
                if a.attempt_id == attempt_id and a.question_id == item.question_id:
                    a.value = item.value
                    a.updated_at = now
                    found = True
                    break
            if not found:
                ans_id = uuid4()
                new_a = AssessmentAnswer(
                    id=ans_id,
                    attempt_id=attempt_id,
                    question_id=item.question_id,
                    value=item.value,
                    updated_at=now,
                )
                self.answers[ans_id] = new_a

    async def get_result_by_attempt_id(self, attempt_id: UUID) -> Optional[AssessmentResult]:
        for r in self.results.values():
            if r.attempt_id == attempt_id:
                return r
        return None

    async def get_result_by_id(self, result_id: UUID, user_id: UUID) -> Optional[AssessmentResult]:
        r = self.results.get(result_id)
        if r and r.user_id == user_id:
            return r
        return None

    async def get_latest_result(self, user_id: UUID) -> Optional[AssessmentResult]:
        user_results = [r for r in self.results.values() if r.user_id == user_id]
        if not user_results:
            return None
        user_results.sort(key=lambda r: r.version, reverse=True)
        return user_results[0]

    async def get_results_for_user(self, user_id: UUID) -> List[AssessmentResult]:
        user_results = [r for r in self.results.values() if r.user_id == user_id]
        user_results.sort(key=lambda r: r.version, reverse=True)
        return user_results

    async def get_next_result_version(self, user_id: UUID) -> int:
        versions = [r.version for r in self.results.values() if r.user_id == user_id]
        return max(versions, default=0) + 1

    async def save_result(self, result: AssessmentResult) -> AssessmentResult:
        if not result.id:
            result.id = uuid4()
        if not getattr(result, "created_at", None):
            result.created_at = datetime.now(timezone.utc)
        self.results[result.id] = result
        return result


class InMemoryProfileRepo:
    def __init__(self, profiles_dict: Dict[UUID, StudentProfile]) -> None:
        self.profiles = profiles_dict

    async def get_by_user_id(self, user_id: UUID) -> Optional[StudentProfile]:
        for p in self.profiles.values():
            if p.user_id == user_id:
                return p
        return None

    async def upsert_profile(
        self,
        user_id: UUID,
        name: Optional[str] = None,
        budget_level: Optional[str] = None,
        hours_available_per_week: Optional[int] = None,
        subjects_of_interest: Optional[List[str]] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
    ) -> StudentProfile:
        p = await self.get_by_user_id(user_id)
        now = datetime.now(timezone.utc)
        if not p:
            pid = uuid4()
            p = StudentProfile(
                id=pid,
                user_id=user_id,
                name=name,
                budget_level=budget_level,
                hours_available_per_week=hours_available_per_week,
                subjects_of_interest=subjects_of_interest or [],
                skills=skills or [],
                created_at=now,
                updated_at=now,
            )
            self.profiles[pid] = p
        else:
            if name is not None:
                p.name = name
            if budget_level is not None:
                p.budget_level = budget_level
            if hours_available_per_week is not None:
                p.hours_available_per_week = hours_available_per_week
            if subjects_of_interest is not None:
                p.subjects_of_interest = subjects_of_interest
            if skills is not None:
                p.skills = skills
            p.updated_at = now
        return p


class InMemoryShortlistRepo:
    def __init__(self, shortlist_dict: Dict[Any, UserShortlist], careers_dict: Dict[UUID, Career]) -> None:
        self.shortlists = shortlist_dict
        self.careers = careers_dict

    async def get_count(self, user_id: UUID) -> int:
        return sum(1 for (uid, _), item in self.shortlists.items() if uid == user_id)

    async def get_item(self, user_id: UUID, career_id: UUID) -> Optional[UserShortlist]:
        item = self.shortlists.get((user_id, career_id))
        if item and item.career is None:
            item.career = self.careers.get(career_id)
        return item

    async def list_for_user(self, user_id: UUID) -> List[UserShortlist]:
        res = []
        for (uid, cid), item in self.shortlists.items():
            if uid == user_id:
                if item.career is None:
                    item.career = self.careers.get(cid)
                res.append(item)
        res.sort(key=lambda x: x.created_at, reverse=True)
        return res

    async def add_item(self, user_id: UUID, career_id: UUID) -> UserShortlist:
        if (user_id, career_id) in self.shortlists:
            return self.shortlists[(user_id, career_id)]
        now = datetime.now(timezone.utc)
        item = UserShortlist(
            user_id=user_id,
            career_id=career_id,
            created_at=now,
        )
        item.career = self.careers.get(career_id)
        self.shortlists[(user_id, career_id)] = item
        return item

    async def remove_item(self, user_id: UUID, career_id: UUID) -> bool:
        if (user_id, career_id) in self.shortlists:
            del self.shortlists[(user_id, career_id)]
            return True
        return False


class InMemoryCompatibilityRepo:
    def __init__(self, snapshots_dict: Dict[UUID, UserCareerCompatibilitySnapshot], careers_dict: Dict[UUID, Career]) -> None:
        self.snapshots = snapshots_dict
        self.careers = careers_dict
        self._counter = 0

    async def get_latest_snapshot(self, user_id: UUID, career_id: UUID) -> Optional[UserCareerCompatibilitySnapshot]:
        matches = [
            s for s in self.snapshots.values()
            if s.user_id == user_id and s.career_id == career_id
        ]
        if not matches:
            return None
        matches.sort(key=lambda x: (x.created_at, getattr(x, "_seq", 0)), reverse=True)
        snap = matches[0]
        if snap.career is None:
            snap.career = self.careers.get(career_id)
        return snap

    async def list_history(self, user_id: UUID, career_id: UUID) -> List[UserCareerCompatibilitySnapshot]:
        matches = [
            s for s in self.snapshots.values()
            if s.user_id == user_id and s.career_id == career_id
        ]
        matches.sort(key=lambda x: (x.created_at, getattr(x, "_seq", 0)), reverse=True)
        for s in matches:
            if s.career is None:
                s.career = self.careers.get(career_id)
        return matches

    async def save_snapshot(self, snapshot: UserCareerCompatibilitySnapshot) -> UserCareerCompatibilitySnapshot:
        self._counter += 1
        snapshot._seq = self._counter
        if not getattr(snapshot, "id", None):
            snapshot.id = uuid4()
        if not getattr(snapshot, "created_at", None):
            snapshot.created_at = datetime.now(timezone.utc)
        if snapshot.career is None:
            snapshot.career = self.careers.get(snapshot.career_id)
        self.snapshots[snapshot.id] = snapshot
        return snapshot


class InMemoryAdaptiveTestRepo:
    def __init__(
        self,
        questions_dict: Dict[UUID, TestQuestionBank],
        attempts_dict: Dict[UUID, TestAttempt],
        answers_dict: Dict[UUID, TestAttemptAnswer],
        careers_dict: Dict[UUID, Career],
    ) -> None:
        self.questions = questions_dict
        self.attempts = attempts_dict
        self.answers = answers_dict
        self.careers = careers_dict

    async def get_question_by_id(self, question_id: UUID) -> Optional[TestQuestionBank]:
        return self.questions.get(question_id)

    async def count_available_questions(
        self,
        topic: str,
        allow_drafts: bool = False,
        language: Optional[str] = None,
    ) -> int:
        count = 0
        for q in self.questions.values():
            if q.topic == topic:
                if not allow_drafts and q.status != "verified":
                    continue
                if language is not None and q.language != language:
                    continue
                count += 1
        return count

    async def pick_next_question(
        self,
        topic: str,
        target_difficulty: int,
        allow_drafts: bool = False,
        language: Optional[str] = None,
        exclude_question_ids: Optional[Set[UUID]] = None,
        recently_seen_ids: Optional[Set[UUID]] = None,
    ) -> Optional[TestQuestionBank]:
        exclude_set = exclude_question_ids or set()
        recent_set = recently_seen_ids or set()

        candidate_diffs = [target_difficulty]
        if target_difficulty == 2:
            candidate_diffs.extend([3, 1])
        elif target_difficulty == 3:
            candidate_diffs.extend([2, 1])
        else:
            candidate_diffs.extend([2, 3])

        for diff in candidate_diffs:
            pool = []
            for q in self.questions.values():
                if q.topic == topic and q.difficulty == diff and q.id not in exclude_set:
                    if not allow_drafts and q.status != "verified":
                        continue
                    if language is not None and q.language != language:
                        continue
                    pool.append(q)

            if not pool:
                continue

            unseen = [q for q in pool if q.id not in recent_set]
            final_pool = unseen if unseen else pool
            final_pool.sort(key=lambda x: str(x.id))
            return final_pool[0]

        return None

    async def get_active_attempt(
        self,
        user_id: UUID,
        topic: str,
    ) -> Optional[TestAttempt]:
        for att in self.attempts.values():
            if att.user_id == user_id and att.topic == topic and att.status == "in_progress":
                att.career = self.careers.get(att.career_id)
                att.answers = [a for a in self.answers.values() if a.attempt_id == att.id]
                att.answers.sort(key=lambda x: x.question_order)
                return att
        return None

    async def get_recent_finished_attempt(
        self,
        user_id: UUID,
        topic: str,
    ) -> Optional[TestAttempt]:
        finished = [
            att for att in self.attempts.values()
            if att.user_id == user_id and att.topic == topic and att.status == "finished"
        ]
        if not finished:
            return None
        finished.sort(key=lambda x: x.finished_at or x.started_at, reverse=True)
        return finished[0]

    async def count_user_starts_since(
        self,
        user_id: UUID,
        since: datetime,
    ) -> int:
        return sum(
            1 for att in self.attempts.values()
            if att.user_id == user_id and att.started_at >= since
        )

    async def get_attempt_by_id(
        self,
        attempt_id: UUID,
        eager_load_answers: bool = True,
    ) -> Optional[TestAttempt]:
        att = self.attempts.get(attempt_id)
        if not att:
            return None
        att.career = self.careers.get(att.career_id)
        att.answers = [a for a in self.answers.values() if a.attempt_id == att.id]
        att.answers.sort(key=lambda x: x.question_order)
        for a in att.answers:
            a.question = self.questions.get(a.question_id)
        return att

    async def get_user_recent_question_ids(
        self,
        user_id: UUID,
        topic: str,
        limit_attempts: int = 3,
    ) -> Set[UUID]:
        user_attempts = [
            att for att in self.attempts.values()
            if att.user_id == user_id and att.topic == topic
        ]
        user_attempts.sort(key=lambda x: x.started_at, reverse=True)
        recent = user_attempts[:limit_attempts]
        recent_ids = set(a.id for a in recent)
        return set(
            ans.question_id for ans in self.answers.values()
            if ans.attempt_id in recent_ids
        )

    async def save_attempt(self, attempt: TestAttempt) -> TestAttempt:
        if not getattr(attempt, "id", None):
            attempt.id = uuid4()
        self.attempts[attempt.id] = attempt
        return attempt

    async def get_answer(
        self,
        attempt_id: UUID,
        question_id: UUID,
    ) -> Optional[TestAttemptAnswer]:
        for ans in self.answers.values():
            if ans.attempt_id == attempt_id and ans.question_id == question_id:
                ans.question = self.questions.get(question_id)
                return ans
        return None

    async def add_answer(self, answer: TestAttemptAnswer) -> TestAttemptAnswer:
        if not getattr(answer, "id", None):
            answer.id = uuid4()
        self.answers[answer.id] = answer
        return answer


class InMemorySkillRepo:
    def __init__(
        self,
        skills: Dict[UUID, Skill],
        evidence: Dict[UUID, SkillEvidence],
        user_skills: Dict[UUID, UserSkill],
    ) -> None:
        self.skills = skills
        self.evidence = evidence
        self.user_skills = user_skills

    async def get_skill_by_id(self, skill_id: UUID) -> Optional[Skill]:
        return self.skills.get(skill_id)

    async def get_skill_by_slug(self, slug: str) -> Optional[Skill]:
        clean = slug.strip().lower()
        for s in self.skills.values():
            if s.slug.lower() == clean:
                return s
        return None

    async def find_skill_by_name_or_alias(self, term: str) -> Optional[Skill]:
        clean = term.strip().lower()
        for s in self.skills.values():
            if s.slug.lower() == clean or s.name.strip().lower() == clean:
                return s
            for a in getattr(s, "aliases", []):
                if str(a).strip().lower() == clean:
                    return s
        return None

    async def get_user_skills(self, user_id: UUID) -> List[UserSkill]:
        res = [us for us in self.user_skills.values() if us.user_id == user_id]
        res.sort(key=lambda x: x.updated_at, reverse=True)
        for us in res:
            us.skill = self.skills.get(us.skill_id)
        return res

    async def get_user_skill(self, user_id: UUID, skill_id: UUID) -> Optional[UserSkill]:
        for us in self.user_skills.values():
            if us.user_id == user_id and us.skill_id == skill_id:
                us.skill = self.skills.get(skill_id)
                return us
        return None

    async def get_skill_evidence_for_user(self, user_id: UUID, skill_id: UUID) -> List[SkillEvidence]:
        res = [e for e in self.evidence.values() if e.user_id == user_id and e.skill_id == skill_id]
        res.sort(key=lambda x: x.created_at)
        return res

    async def get_evidence_by_source(self, source_type: str, source_id: UUID) -> Optional[SkillEvidence]:
        for e in self.evidence.values():
            if e.source_type == source_type and e.source_id == source_id:
                return e
        return None

    async def add_evidence(self, ev: SkillEvidence) -> SkillEvidence:
        if not getattr(ev, "id", None):
            ev.id = uuid4()
        if not getattr(ev, "created_at", None):
            ev.created_at = datetime.now(timezone.utc)
        self.evidence[ev.id] = ev
        return ev

    async def upsert_user_skill(self, user_id: UUID, skill_id: UUID, current_level: str, confidence: str) -> UserSkill:
        now = datetime.now(timezone.utc)
        for us in self.user_skills.values():
            if us.user_id == user_id and us.skill_id == skill_id:
                us.current_level = current_level
                us.confidence = confidence
                us.updated_at = now
                us.skill = self.skills.get(skill_id)
                return us
        us = UserSkill(
            id=uuid4(),
            user_id=user_id,
            skill_id=skill_id,
            current_level=current_level,
            confidence=confidence,
            updated_at=now,
        )
        us.skill = self.skills.get(skill_id)
        self.user_skills[us.id] = us
        return us


class MockSession:
    def __init__(self, storage: Dict[str, Any]) -> None:
        self.storage = storage
        self.user_repo = InMemoryUserRepo(storage["users"])
        self.token_repo = InMemoryTokenRepo(storage["tokens"])
        self.career_repo = InMemoryCareerRepo(storage["careers"])
        self.assessment_repo = InMemoryAssessmentRepo(storage)
        self.profile_repo = InMemoryProfileRepo(storage["student_profiles"])
        self.shortlist_repo = InMemoryShortlistRepo(storage["user_shortlists"], storage["careers"])
        self.compatibility_repo = InMemoryCompatibilityRepo(storage["user_career_compatibility_snapshots"], storage["careers"])
        self.adaptive_test_repo = InMemoryAdaptiveTestRepo(
            storage["test_question_banks"],
            storage["test_attempts"],
            storage["test_attempt_answers"],
            storage["careers"],
        )
        self.adaptive_test_repo.session = self
        self.skill_repo = InMemorySkillRepo(
            storage["skills"],
            storage["skill_evidence"],
            storage["user_skills"],
        )


    def add(self, instance):
        if not getattr(instance, "id", None):
            instance.id = uuid4()
        table_name = getattr(instance, "__tablename__", None)
        if table_name and table_name in self.storage:
            self.storage[table_name][instance.id] = instance

    async def execute(self, stmt):
        class MockResult:
            def __init__(self, val):
                self._val = val

            def scalar_one_or_none(self):
                return self._val

            def scalar(self):
                return self._val

            def scalars(self):
                class MockScalars:
                    def __init__(self, items):
                        self._items = items

                    def all(self):
                        return self._items

                return MockScalars([self._val] if self._val else [])

        try:
            entity = stmt.column_descriptions[0]["entity"]
            table_name = getattr(entity, "__tablename__", None)
            items = list(self.storage.get(table_name, {}).values())

            for clause in getattr(stmt, "_where_criteria", []):
                col_name = getattr(clause.left, "key", None)
                val = getattr(clause.right, "value", None)
                if col_name and val is not None:
                    items = [it for it in items if getattr(it, col_name, None) == val]

            match = items[0] if items else None
            return MockResult(match)
        except Exception:
            return MockResult(None)

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def flush(self):
        pass

    async def refresh(self, instance):
        pass

    async def close(self):
        pass


@pytest_asyncio.fixture
async def test_storage():
    storage = {
        "users": {},
        "tokens": {},
        "versions": {},
        "questions": {},
        "attempts": {},
        "answers": {},
        "careers": {},
        "results": {},
        "exams": {},
        "colleges": {},
        "courses": {},
        "certificates": {},
        "internships": {},
        "student_profiles": {},
        "user_shortlists": {},
        "user_career_compatibility_snapshots": {},
        "test_question_banks": {},
        "test_attempts": {},
        "test_attempt_answers": {},
        "skills": {},
        "skill_evidence": {},
        "user_skills": {},
        "roadmap_templates": {},
        "template_phases": {},
        "template_items": {},
        "roadmaps": {},
        "roadmap_phases": {},
        "roadmap_items": {},
        "replan_history": {},
        "exam_cycles": {},
    }

    # Pre-seed assessment questions
    seed_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "assessment_questions.json"
    if seed_file.is_file():
        with open(seed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        version_id = uuid4()
        ver = AssessmentVersion(
            id=version_id,
            version_number=data["version_number"],
            title=data["title"],
            description=data["description"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        storage["versions"][version_id] = ver
        for q in data["questions"]:
            qid = uuid4()
            q_rec = AssessmentQuestion(
                id=qid,
                assessment_version_id=version_id,
                question_order=q["order"],
                text=q["text"],
                dimension=q["dimension"],
                reverse_scored=q["reverse_scored"],
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            storage["questions"][qid] = q_rec

    # Pre-seed from catalog if available, else from careers.json
    catalog_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "career_catalog.json"
    if catalog_file.is_file():
        with open(catalog_file, "r", encoding="utf-8") as f:
            cdata = json.load(f)

        exam_map = {}
        for item in cdata.get("exams", []):
            eid = uuid4()
            e = Exam(
                id=eid,
                code=item["code"],
                name=item["name"],
                description=item["description"],
                conducting_body=item["conducting_body"],
                exam_level=item["exam_level"],
                registration_url=item.get("registration_url"),
                source_url=item["source_url"],
                status=item.get("status", "draft"),
                created_at=datetime.now(timezone.utc),
            )
            exam_map[item["code"]] = e
            storage["exams"][eid] = e

        college_map = {}
        for item in cdata.get("colleges", []):
            cid = uuid4()
            c = College(
                id=cid,
                name=item["name"],
                location=item["location"],
                official_url=item["official_url"],
                fees=item.get("fees"),
                cutoffs=item.get("cutoffs"),
                nirf_rank=item.get("nirf_rank"),
                source_url=item["source_url"],
                status=item.get("status", "draft"),
                created_at=datetime.now(timezone.utc),
            )
            college_map[item["name"]] = c
            storage["colleges"][cid] = c

        course_map = {}
        for item in cdata.get("courses", []):
            crid = uuid4()
            cr = Course(
                id=crid,
                code=item["code"],
                title=item["title"],
                degree_level=item["degree_level"],
                duration=item["duration"],
                description=item["description"],
                source_url=item["source_url"],
                status=item.get("status", "draft"),
                created_at=datetime.now(timezone.utc),
            )
            course_map[item["code"]] = cr
            storage["courses"][crid] = cr

        cert_map = {}
        for item in cdata.get("certificates", []):
            ctid = uuid4()
            ct = Certificate(
                id=ctid,
                code=item["code"],
                name=item["name"],
                issuing_organization=item["issuing_organization"],
                description=item["description"],
                url=item.get("url"),
                source_url=item["source_url"],
                status=item.get("status", "draft"),
                created_at=datetime.now(timezone.utc),
            )
            cert_map[item["code"]] = ct
            storage["certificates"][ctid] = ct

        intern_map = {}
        for item in cdata.get("internships", []):
            iid = uuid4()
            intern = Internship(
                id=iid,
                code=item["code"],
                title=item["title"],
                domain=item["domain"],
                stipend_range=item.get("stipend_range"),
                duration_months=item.get("duration_months"),
                locations=item.get("locations", []),
                description=item["description"],
                source_url=item["source_url"],
                status=item.get("status", "draft"),
                created_at=datetime.now(timezone.utc),
            )
            intern_map[item["code"]] = intern
            storage["internships"][iid] = intern

        career_map = {}
        for c in cdata.get("careers", []):
            cid = uuid4()
            career = Career(
                id=cid,
                code=c["code"],
                title=c["title"],
                cluster=c["cluster"],
                aliases=c.get("aliases", []),
                overview=c["overview"],
                description=c.get("description"),
                day_in_life=c.get("day_in_life"),
                salary_ranges=c.get("salary_ranges"),
                demand=c.get("demand", "moderate"),
                time_to_job_ready_months=c.get("time_to_job_ready_months"),
                entrance_difficulty=c.get("entrance_difficulty"),
                required_skills=c.get("required_skills", []),
                education_paths=c.get("education_paths", []),
                status=c.get("status", "draft"),
                source_url=c["source_url"],
                dimension_weights=c["dimension_weights"],
                created_at=datetime.now(timezone.utc),
            )
            career.exams = [exam_map[x] for x in c.get("exam_codes", []) if x in exam_map]
            career.colleges = [college_map[x] for x in c.get("college_names", []) if x in college_map]
            career.courses = [course_map[x] for x in c.get("course_codes", []) if x in course_map]
            career.certificates = [cert_map[x] for x in c.get("certificate_codes", []) if x in cert_map]
            career.internships = [intern_map[x] for x in c.get("internship_codes", []) if x in intern_map]
            career_map[c["code"]] = career
            storage["careers"][cid] = career

        # Related careers linking
        for c in cdata.get("careers", []):
            career = career_map[c["code"]]
            career.related_careers = [
                career_map[rc]
                for rc in c.get("related_career_codes", [])
                if rc in career_map and career_map[rc].id != career.id
            ]

    # Pre-seed diagnostic test questions
    tq_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "test_questions.json"
    if tq_file.is_file():
        with open(tq_file, "r", encoding="utf-8") as f:
            tq_data = json.load(f)
        for q in tq_data.get("questions", []):
            qid = UUID(q["id"])
            q_rec = TestQuestionBank(
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
                created_at=datetime.now(timezone.utc),
            )
            storage["test_question_banks"][qid] = q_rec

    # Pre-seed skills catalog
    sk_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "skills_catalog.json"
    if sk_file.is_file():
        with open(sk_file, "r", encoding="utf-8") as f:
            sk_data = json.load(f)
        for item in sk_data.get("skills", []):
            sid = UUID(item["id"])
            skill = Skill(
                id=sid,
                slug=item["slug"],
                name=item["name"],
                description=item.get("description"),
                aliases=item.get("aliases", []),
                category=item.get("category", "General"),
                created_at=datetime.now(timezone.utc),
            )
            storage["skills"][sid] = skill

    # Pre-seed exam cycles
    ec_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "exam_cycles.json"
    if ec_file.is_file():
        with open(ec_file, "r", encoding="utf-8") as f:
            ec_data = json.load(f)
        for item in ec_data.get("exam_cycles", []):
            exam = next((e for e in storage["exams"].values() if e.code == item["exam_code"]), None)
            if exam:
                cid = uuid4()
                cycle = ExamCycle(
                    id=cid,
                    exam_id=exam.id,
                    year=item["year"],
                    registration_start=datetime.fromisoformat(item["registration_start"].replace("Z", "+00:00")) if item.get("registration_start") else None,
                    registration_end=datetime.fromisoformat(item["registration_end"].replace("Z", "+00:00")) if item.get("registration_end") else None,
                    exam_date=datetime.fromisoformat(item["exam_date"].replace("Z", "+00:00")) if item.get("exam_date") else None,
                    source_url=item["source_url"],
                    status=item.get("status", "draft"),
                    created_at=datetime.now(timezone.utc),
                )
                cycle.exam = exam
                storage["exam_cycles"][cid] = cycle

    # Pre-seed roadmap templates
    rt_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "roadmap_templates.json"
    if rt_file.is_file():
        with open(rt_file, "r", encoding="utf-8") as f:
            rt_data = json.load(f)
        for tmpl_data in rt_data.get("templates", []):
            career = next((c for c in storage["careers"].values() if c.code == tmpl_data["career_code"]), None)
            if career:
                tid = uuid4()
                tmpl = RoadmapTemplate(
                    id=tid,
                    career_id=career.id,
                    version=tmpl_data["version"],
                    title=tmpl_data["title"],
                    description=tmpl_data.get("description"),
                    status=tmpl_data.get("status", "draft"),
                    created_at=datetime.now(timezone.utc),
                )
                tmpl.career = career
                storage["roadmap_templates"][tid] = tmpl

                phase_map = {}
                for p_data in tmpl_data.get("phases", []):
                    pid = uuid4()
                    phase = TemplatePhase(
                        id=pid,
                        template_id=tid,
                        name=p_data["name"],
                        phase_order=p_data["phase_order"],
                        description=p_data.get("description"),
                        created_at=datetime.now(timezone.utc),
                    )
                    phase.template = tmpl
                    storage["template_phases"][pid] = phase
                    phase_map[p_data["phase_order"]] = phase

                for it_data in tmpl_data.get("items", []):
                    iid = uuid4()
                    sk = next((s for s in storage["skills"].values() if s.slug == it_data.get("skill_slug")), None)
                    p_obj = phase_map.get(it_data.get("phase_order"))
                    item = TemplateItem(
                        id=iid,
                        template_id=tid,
                        phase_id=p_obj.id if p_obj else None,
                        item_code=it_data.get("item_code"),
                        type=it_data["type"],
                        title=it_data["title"],
                        source_url=it_data.get("source_url"),
                        estimated_minutes=it_data.get("estimated_minutes", 60),
                        difficulty=it_data.get("difficulty", 1),
                        topic=it_data["topic"],
                        skill_id=sk.id if sk else None,
                        prerequisites=it_data.get("prerequisites", []),
                        optional=it_data.get("optional", False),
                        status=it_data.get("status", "draft"),
                        sequence_order=it_data.get("sequence_order", 0),
                        extra_data=it_data.get("extra_data", {}),
                        created_at=datetime.now(timezone.utc),
                    )
                    item.template = tmpl
                    item.skill = sk
                    storage["template_items"][iid] = item

    return storage


@pytest_asyncio.fixture
async def async_client(test_storage, monkeypatch):
    mock_session = MockSession(test_storage)

    from app.services.auth_service import AuthService
    from app.services.assessment_service import AssessmentService
    from app.services.career_service import CareerService
    from app.services.profile_service import ProfileService
    from app.services.compatibility_service import CompatibilityService
    from app.services.adaptive_test_service import AdaptiveTestService
    from app.services.skill_service import SkillService
    from app.api.deps import UserRepository

    def mock_auth_init(self, session):
        self.session = mock_session
        self.user_repo = mock_session.user_repo
        self.token_repo = mock_session.token_repo

    monkeypatch.setattr(AuthService, "__init__", mock_auth_init)

    def mock_assessment_init(self, session, gateway=None):
        self.session = mock_session
        self.repo = mock_session.assessment_repo
        self.career_repo = mock_session.career_repo
        self.gateway = gateway or LLMGateway(provider=MockLLMProvider())

    monkeypatch.setattr(AssessmentService, "__init__", mock_assessment_init)

    def mock_career_service_init(self, session):
        self.session = mock_session
        self.repo = mock_session.career_repo
        self.assessment_repo = mock_session.assessment_repo

    monkeypatch.setattr(CareerService, "__init__", mock_career_service_init)

    def mock_profile_service_init(self, session):
        self.session = mock_session
        self.profile_repo = mock_session.profile_repo

    monkeypatch.setattr(ProfileService, "__init__", mock_profile_service_init)

    def mock_compatibility_service_init(self, session):
        self.session = mock_session
        self.career_repo = mock_session.career_repo
        self.assessment_repo = mock_session.assessment_repo
        self.profile_repo = mock_session.profile_repo
        self.shortlist_repo = mock_session.shortlist_repo
        self.compatibility_repo = mock_session.compatibility_repo

    monkeypatch.setattr(CompatibilityService, "__init__", mock_compatibility_service_init)

    def mock_adaptive_test_service_init(self, session):
        self.session = mock_session
        self.repo = mock_session.adaptive_test_repo
        self.career_repo = mock_session.career_repo

    monkeypatch.setattr(AdaptiveTestService, "__init__", mock_adaptive_test_service_init)

    def mock_skill_service_init(self, session):
        self.session = mock_session
        self.repo = mock_session.skill_repo

    monkeypatch.setattr(SkillService, "__init__", mock_skill_service_init)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    async def mock_get_by_id(self, user_id):
        return await mock_session.user_repo.get_by_id(user_id)

    monkeypatch.setattr(UserRepository, "get_by_id", mock_get_by_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
