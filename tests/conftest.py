import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.auth import RefreshToken
from app.models.user import User


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
            user.id = uuid.uuid4()
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
        token_id = uuid.uuid4()
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


class MockSession:
    """Mock session providing atomic commit/rollback for test isolation."""
    def __init__(self, users_dict, tokens_dict):
        self.user_repo = InMemoryUserRepo(users_dict)
        self.token_repo = InMemoryTokenRepo(tokens_dict)

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
    return {
        "users": {},
        "tokens": {},
    }


@pytest_asyncio.fixture
async def async_client(test_storage, monkeypatch):
    mock_session = MockSession(test_storage["users"], test_storage["tokens"])

    # Wire AuthService and Repositories to test storage
    from app.services.auth_service import AuthService
    from app.api.deps import UserRepository

    def mock_auth_init(self, session):
        self.session = mock_session
        self.user_repo = mock_session.user_repo
        self.token_repo = mock_session.token_repo

    monkeypatch.setattr(AuthService, "__init__", mock_auth_init)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    # Wire deps.get_current_user to use our test user repo

    async def mock_get_by_id(self, user_id):
        return await mock_session.user_repo.get_by_id(user_id)

    monkeypatch.setattr(UserRepository, "get_by_id", mock_get_by_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
