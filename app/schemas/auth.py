import re
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_password_strength(v: str) -> str:
    if len(v) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    if len(v.encode("utf-8")) > 72:
        raise ValueError("Password cannot exceed 72 bytes due to encryption constraints.")
    return v


def validate_email_format(v: str) -> str:
    clean = v.strip().lower()
    if not EMAIL_REGEX.match(clean):
        raise ValueError("Invalid email address format.")
    return clean


class UserSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Plain password (min 10 chars, max 72 bytes)")
    education_level: Literal["class_11_12", "college"] = Field(
        ...,
        description="Target educational tier: 'class_11_12' or 'college'",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return validate_email_format(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return validate_email_format(v)


class TokenRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=20)


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=20)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    education_level: str
    is_active: bool
    created_at: datetime


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return validate_email_format(v)


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=20)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)
