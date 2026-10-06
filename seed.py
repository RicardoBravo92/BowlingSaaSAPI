import asyncio
import os

from sqlmodel import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import get_password_hash
from app.models.enums import UserRole
from app.models.user import User
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Passwords come from the environment. In production they are mandatory:
# hardcoded weak credentials must never be seeded into a real deployment.
SEED_PASSWORDS = {
    "owner": os.environ.get("SEED_OWNER_PASSWORD"),
    "manager": os.environ.get("SEED_MANAGER_PASSWORD"),
    "cashier": os.environ.get("SEED_CASHIER_PASSWORD"),
    "maintenance": os.environ.get("SEED_MAINTENANCE_PASSWORD"),
    "user": os.environ.get("SEED_USER_PASSWORD"),
}

if settings.APP_ENV == "production":
    missing = [name for name, pw in SEED_PASSWORDS.items() if not pw]
    if missing:
        raise RuntimeError(
            "Missing SEED_*_PASSWORD environment variables in production: "
            + ", ".join(f"SEED_{name.upper()}_PASSWORD" for name in missing)
        )


def _default_password(role: str) -> str:
    """Dev-only fallback so `python seed.py` works locally without env vars."""
    if settings.APP_ENV == "production":
        return SEED_PASSWORDS[role]  # guaranteed non-empty above
    return SEED_PASSWORDS[role] or f"{role}password123"


async def seed_users():
    logger.info("Starting database seeding...")

    users_to_create = [
        {
            "full_name": "Initial Owner",
            "email": "owner@bowlingsaas.com",
            "password": _default_password("owner"),
            "role": UserRole.OWNER,
        },
        {
            "full_name": "General Manager",
            "email": "manager@bowlingsaas.com",
            "password": _default_password("manager"),
            "role": UserRole.MANAGER,
        },
        {
            "full_name": "Main Cashier",
            "email": "cashier@bowlingsaas.com",
            "password": _default_password("cashier"),
            "role": UserRole.CASHIER,
        },
        {
            "full_name": "Technician One",
            "email": "maintenance@bowlingsaas.com",
            "password": _default_password("maintenance"),
            "role": UserRole.MAINTENANCE,
        },
        {
            "full_name": "Regular Customer",
            "email": "user@gmail.com",
            "password": _default_password("user"),
            "role": UserRole.USER,
        },
    ]

    async with AsyncSessionLocal() as session:
        for user_data in users_to_create:
            # Check if user already exists
            statement = select(User).where(User.email == user_data["email"])
            results = await session.execute(statement)
            existing_user = results.scalar_one_or_none()

            if not existing_user:
                logger.info(f"Creating user: {user_data['full_name']} ({user_data['role']})")
                new_user = User(
                    full_name=user_data["full_name"],
                    email=user_data["email"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                )
                session.add(new_user)
            else:
                logger.info(f"User {user_data['email']} already exists, skipping.")

        await session.commit()

    logger.info("Seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_users())