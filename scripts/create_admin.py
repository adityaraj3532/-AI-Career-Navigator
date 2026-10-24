"""Dedicated CLI for Explicit Admin Account Creation.

Security Invariants:
1. Refuses to run in production (ENV=production).
2. Uses example.com default addresses (admin@example.com).
3. Reads password from ADMIN_PASSWORD env var or generates once with secrets.token_urlsafe(16).
4. Prints password once to stdout; NEVER logs or hardcodes passwords.
5. Admin creation is completely separated from demo seeding and database setup scripts.

Usage:
    python -m scripts.create_admin [--email EMAIL] [--password PASSWORD]
"""

import argparse
import asyncio
import logging
import os
from pathlib import Path
import secrets
import sys
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger("scripts.create_admin")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def assert_not_production() -> None:
    settings = get_settings()
    env = os.getenv("ENV", settings.ENVIRONMENT).strip().lower()
    if env == "production":
        raise RuntimeError("CRITICAL SECURITY ERROR: Admin creation CLI is refused in production environment.")


async def create_or_update_admin(
    session: AsyncSession,
    email: str = "admin@example.com",
    password: Optional[str] = None,
    education_level: str = "college",
) -> tuple[User, str, bool]:
    """Create or update admin account. Returns (user, plaintext_password, was_created)."""
    assert_not_production()

    clean_email = email.strip().lower()
    if not password:
        password = os.getenv("ADMIN_PASSWORD")
    if not password:
        password = secrets.token_urlsafe(16)

    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password cannot exceed 72 bytes.")

    stmt = select(User).where(User.email == clean_email)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if user:
        user.hashed_password = hash_password(password)
        user.role = "admin"
        user.is_active = True
        user.is_demo = False
        was_created = False
    else:
        user = User(
            email=clean_email,
            hashed_password=hash_password(password),
            role="admin",
            education_level=education_level,
            is_active=True,
            is_demo=False,
        )
        session.add(user)
        was_created = True

    await session.commit()
    return user, password, was_created


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an admin account")
    parser.add_argument("--email", default="admin@example.com", help="Admin email address (default: admin@example.com)")
    parser.add_argument("--password", default=None, help="Optional admin password (otherwise read from ADMIN_PASSWORD env or securely generated)")
    parser.add_argument("--education-level", default="college", choices=["class_11_12", "college"])

    args = parser.parse_args()

    assert_not_production()

    async def _run():
        async with async_session_factory() as session:
            user, pw, was_created = await create_or_update_admin(
                session=session,
                email=args.email,
                password=args.password,
                education_level=args.education_level,
            )

        action = "Created" if was_created else "Updated"
        print("\n=======================================================")
        print(f" ADMIN ACCOUNT {action.upper()} SUCCESSFULLY")
        print("=======================================================")
        print(f" Email:    {user.email}")
        print(f" Password: {pw}")
        print(" (Save this password immediately; it will not be displayed again or logged)")
        print("=======================================================\n")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
