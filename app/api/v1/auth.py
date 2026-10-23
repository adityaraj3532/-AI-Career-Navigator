from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LogoutRequest,
    MessageResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new student account",
)
async def signup(
    req: UserSignupRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    service = AuthService(session)
    return await service.signup(req)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
)
async def login(
    req: UserLoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    service = AuthService(session)
    return await service.login(req)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue new access token",
)
async def refresh_tokens(
    req: TokenRefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    service = AuthService(session)
    return await service.refresh(req)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke current refresh token family",
)
async def logout(
    req: LogoutRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    service = AuthService(session)
    await service.logout(req.refresh_token)
    return MessageResponse(message="Successfully logged out.")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Revoke all active sessions for current user",
)
async def logout_all(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    service = AuthService(session)
    await service.logout_all(current_user.id)
    return MessageResponse(message="All active sessions have been terminated.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password and invalidate all active sessions",
)
async def change_password(
    req: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    service = AuthService(session)
    await service.change_password(current_user.id, req)
    return MessageResponse(message="Password changed successfully. All sessions revoked.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get profile of current authenticated user",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        education_level=current_user.education_level,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
