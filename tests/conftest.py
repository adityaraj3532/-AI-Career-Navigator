import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.assessment import (
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentVersion,
)
from app.models.auth import RefreshToken
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


class InMemoryAssessmentRepo:
    def __init__(self, storage: Dict[str, Any]) -> None:
        self.versions: Dict[UUID, AssessmentVersion] = storage["versions"]
        self.questions: Dict[UUID, AssessmentQuestion] = storage["questions"]
        self.attempts: Dict[UUID, AssessmentAttempt] = storage["attempts"]
        self.answers: Dict[UUID, AssessmentAnswer] = storage["answers"]

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
            # Check existing answer
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


class MockSession:
    def __init__(self, storage: Dict[str, Any]) -> None:
        self.user_repo = InMemoryUserRepo(storage["users"])
        self.token_repo = InMemoryTokenRepo(storage["tokens"])
        self.assessment_repo = InMemoryAssessmentRepo(storage)

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

    return storage


@pytest_asyncio.fixture
async def async_client(test_storage, monkeypatch):
    mock_session = MockSession(test_storage)

    from app.services.auth_service import AuthService
    from app.services.assessment_service import AssessmentService
    from app.api.deps import UserRepository

    def mock_auth_init(self, session):
        self.session = mock_session
        self.user_repo = mock_session.user_repo
        self.token_repo = mock_session.token_repo

    monkeypatch.setattr(AuthService, "__init__", mock_auth_init)

    def mock_assessment_init(self, session):
        self.session = mock_session
        self.repo = mock_session.assessment_repo

    monkeypatch.setattr(AssessmentService, "__init__", mock_assessment_init)

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
