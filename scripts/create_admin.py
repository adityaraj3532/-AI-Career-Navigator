import argparse
import asyncio
import sys
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


async def create_admin(email: str, password: str, education_level: str = "college") -> None:
    if len(password) < 10:
        print("Error: Password must be at least 10 characters long.", file=sys.stderr)
        sys.exit(1)
    if len(password.encode("utf-8")) > 72:
        print("Error: Password cannot exceed 72 bytes.", file=sys.stderr)
        sys.exit(1)

    clean_email = email.strip().lower()

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        existing = await user_repo.get_by_email(clean_email)
        if existing:
            print(f"Error: An account with email '{clean_email}' already exists.", file=sys.stderr)
            sys.exit(1)

        hashed = hash_password(password)
        admin_user = User(
            email=clean_email,
            hashed_password=hashed,
            role="admin",
            education_level=education_level,
            is_active=True,
        )
        created = await user_repo.create(admin_user)
        await session.commit()
        print(f"Admin account created successfully! ID: {created.id}, Email: {created.email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin user for AI Career Navigator.")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password (min 10 chars, max 72 bytes)")
    parser.add_argument("--education-level", default="college", choices=["class_11_12", "college"])
    args = parser.parse_args()

    asyncio.run(create_admin(args.email, args.password, args.education_level))


if __name__ == "__main__":
    main()
