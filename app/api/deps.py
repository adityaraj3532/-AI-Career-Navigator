from typing import Annotated, Optional
from uuid import UUID
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

# Strict Bearer token extractor - zero fallback test headers allowed
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    auth_header: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not auth_header or not auth_header.credentials:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_REQUIRED",
            message="Bearer authentication token is required.",
        )

    token = auth_header.credentials

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_EXPIRED",
            message="Access token has expired.",
        )
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_TOKEN",
            message=f"Invalid authentication token: {exc}",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_TOKEN",
            message="Token subject claim is missing.",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_TOKEN",
            message="Token subject is not a valid UUID.",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="USER_NOT_FOUND",
            message="The authenticated user no longer exists.",
        )

    if not user.is_active:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="USER_INACTIVE",
            message="Account is disabled.",
        )

    return user


async def get_optional_current_user(
    auth_header: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """Extracts current user if valid bearer token is provided; returns None otherwise."""
    if not auth_header or not auth_header.credentials:
        return None

    try:
        payload = decode_access_token(auth_header.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = UUID(user_id_str)
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None
