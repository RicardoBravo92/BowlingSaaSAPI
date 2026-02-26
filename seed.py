import asyncio
from sqlmodel import select
from app.core.database import AsyncSessionLocal, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.models.enums import UserRole
from app.core.logging_config import get_logger

logger = get_logger(__name__)

async def seed_users():
    logger.info("Starting database seeding...")
    
    users_to_create = [
        {
            "full_name": "Initial Owner",
            "email": "owner@bowlingsaas.com",
            "password": "ownerpassword123",
            "role": UserRole.OWNER
        },
        {
            "full_name": "General Manager",
            "email": "manager@bowlingsaas.com",
            "password": "managerpassword123",
            "role": UserRole.MANAGER
        },
        {
            "full_name": "Main Cashier",
            "email": "cashier@bowlingsaas.com",
            "password": "cashierpassword123",
            "role": UserRole.CASHIER
        },
        {
            "full_name": "Technician One",
            "email": "maintenance@bowlingsaas.com",
            "password": "maintenancepassword123",
            "role": UserRole.MAINTENANCE
        },
        {
            "full_name": "Regular Customer",
            "email": "user@gmail.com",
            "password": "userpassword123",
            "role": UserRole.USER
        }
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
                    role=user_data["role"]
                )
                session.add(new_user)
            else:
                logger.info(f"User {user_data['email']} already exists, skipping.")
        
        await session.commit()
    
    logger.info("Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_users())
