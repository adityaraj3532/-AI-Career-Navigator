import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID
import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

# Pre-computed dummy bcrypt hash to protect against timing attacks on login
DUMMY_BCRYPT_HASH = "$2b$12$K8j7mB4eO0QpZ1rT3wY6Lu9fF5vX2cE8hN1sI4aG7dJ0kM3oP6qTy"


def hash_password(password: str) -> str:
    """Hashes a password with bcrypt. Enforces max 72 bytes (bcrypt input boundary)."""
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        raise ValueError("Password cannot exceed 72 bytes.")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    try:
        pw_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False


def verify_dummy_password(plain_password: str) -> None:
    """Runs a real bcrypt hash check against a dummy hash to neutralize timing attacks."""
    try:
        pw_bytes = plain_password.encode("utf-8")[:72]
        bcrypt.checkpw(pw_bytes, DUMMY_BCRYPT_HASH.encode("utf-8"))
    except Exception:
        pass


def create_access_token(user_id: UUID, email: str, role: str) -> str:
    """Creates a signed JWT access token valid for 15 minutes.
    
    Enforces algorithm pinning (HS256) and explicit required claims:
    'exp', 'iat', 'sub', 'type'='access'.
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT access token.
    
    Rejects 'none' or mismatched algorithms; requires 'exp', 'iat', 'sub', and 'type'='access'.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=["HS256"],
        options={"require": ["exp", "iat", "sub", "type"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Token is not an access token.")
    return payload


def generate_opaque_token() -> str:
    """Generates an opaque, cryptographically secure 48-byte URL-safe string."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Computes the SHA-256 hex digest of an opaque token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
