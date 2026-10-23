import logging
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_dummy_password,
    verify_password,
)
from app.models.user import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
)

logger = logging.getLogger("app.services.auth")
settings = get_settings()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = TokenRepository(session)

    async def signup(self, req: UserSignupRequest) -> UserResponse:
        existing = await self.user_repo.get_by_email(req.email)
        if existing:
            raise AppException(
                status_code=409,
                code="EMAIL_ALREADY_EXISTS",
                message="An account with this email address already exists.",
            )

        hashed_pw = hash_password(req.password)
        # Signups are strictly assigned the 'student' role
        new_user = User(
            email=req.email,
            hashed_password=hashed_pw,
            role="student",
            education_level=req.education_level,
            is_active=True,
        )
        created_user = await self.user_repo.create(new_user)
        await self.session.commit()
        return UserResponse(
            id=created_user.id,
            email=created_user.email,
            role=created_user.role,
            education_level=created_user.education_level,
            is_active=created_user.is_active,
            created_at=created_user.created_at,
        )

    async def login(self, req: UserLoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(req.email)
        if not user:
            # Neutralize timing attack with real bcrypt check against dummy hash
            verify_dummy_password(req.password)
            raise AppException(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Invalid email or password.",
            )

        if not verify_password(req.password, user.hashed_password):
            raise AppException(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Invalid email or password.",
            )

        if not user.is_active:
            raise AppException(
                status_code=403,
                code="USER_INACTIVE",
                message="Your account is currently disabled.",
            )

        # Issue tokens
        access_token = create_access_token(user.id, user.email, user.role)
        raw_refresh_token = generate_opaque_token()
        refresh_hash = hash_token(raw_refresh_token)

        family_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self.token_repo.create_refresh_token(
            user_id=user.id,
            family_id=family_id,
            token_hash=refresh_hash,
            expires_at=expires_at,
        )
        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, req: TokenRefreshRequest) -> TokenResponse:
        token_hash = hash_token(req.refresh_token)
        token_record = await self.token_repo.get_by_hash(token_hash)

        if not token_record:
            raise AppException(
                status_code=401,
                code="INVALID_REFRESH_TOKEN",
                message="Invalid or unrecognized refresh token.",
            )

        # Token Reuse Detection: if token is already used or revoked, revoke entire family
        if token_record.used_at is not None or token_record.revoked_at is not None:
            logger.warning(
                "Refresh token reuse detected for family_id=%s. Revoking entire token family.",
                token_record.family_id,
            )
            await self.token_repo.revoke_family(token_record.family_id)
            await self.session.commit()
            raise AppException(
                status_code=401,
                code="REFRESH_TOKEN_REUSE_DETECTED",
                message="Token reuse detected. All active sessions in this family have been terminated.",
            )

        now = datetime.now(timezone.utc)
        if token_record.expires_at < now:
            raise AppException(
                status_code=401,
                code="REFRESH_TOKEN_EXPIRED",
                message="Refresh token has expired. Please log in again.",
            )

        user = await self.user_repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise AppException(
                status_code=401,
                code="USER_NOT_FOUND",
                message="User associated with token is not active.",
            )

        # Mark current token as used
        await self.token_repo.mark_token_used(token_record.id)

        # Rotate: issue new opaque refresh token belonging to the SAME family
        new_raw_refresh = generate_opaque_token()
        new_refresh_hash = hash_token(new_raw_refresh)
        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self.token_repo.create_refresh_token(
            user_id=user.id,
            family_id=token_record.family_id,
            token_hash=new_refresh_hash,
            expires_at=new_expires_at,
        )

        access_token = create_access_token(user.id, user.email, user.role)
        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        token_record = await self.token_repo.get_by_hash(token_hash)
        if token_record and token_record.revoked_at is None:
            await self.token_repo.revoke_family(token_record.family_id)
            await self.session.commit()

    async def logout_all(self, user_id: UUID) -> None:
        await self.token_repo.revoke_user_tokens(user_id)
        await self.session.commit()

    async def change_password(
        self,
        user_id: UUID,
        req: ChangePasswordRequest,
    ) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise AppException(
                status_code=404,
                code="USER_NOT_FOUND",
                message="User not found.",
            )

        if not verify_password(req.current_password, user.hashed_password):
            raise AppException(
                status_code=400,
                code="INVALID_CURRENT_PASSWORD",
                message="The current password provided is incorrect.",
            )

        new_hashed = hash_password(req.new_password)
        await self.user_repo.update_password(user_id, new_hashed)
        # Password change terminates all active refresh sessions
        await self.token_repo.revoke_user_tokens(user_id)
        await self.session.commit()

    async def forgot_password(self, req: ForgotPasswordRequest) -> None:
        user = await self.user_repo.get_by_email(req.email)
        if not user or not user.is_active:
            # Timing mitigation: perform dummy password verification work to prevent enumeration
            verify_dummy_password("dummy_constant_password_123")
            return

        raw_token = generate_opaque_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        await self.token_repo.create_password_reset_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self.session.commit()

        # Enqueue ARQ email dispatch job
        logger.info("Enqueued password reset email to %s with token %s", req.email, raw_token)

    async def reset_password(self, req: ResetPasswordRequest) -> None:
        token_hash = hash_token(req.token)
        token_record = await self.token_repo.get_password_reset_token_by_hash(token_hash)

        now = datetime.now(timezone.utc)
        if not token_record or token_record.used_at is not None or token_record.expires_at < now:
            raise AppException(
                status_code=400,
                code="INVALID_OR_EXPIRED_RESET_TOKEN",
                message="The password reset token is invalid or has expired.",
            )

        new_hashed = hash_password(req.new_password)
        await self.user_repo.update_password(token_record.user_id, new_hashed)
        await self.token_repo.mark_password_reset_token_used(token_record.id)
        # Revoke all active refresh sessions for security
        await self.token_repo.revoke_user_tokens(token_record.user_id)
        await self.session.commit()
