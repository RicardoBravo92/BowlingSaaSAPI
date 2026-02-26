from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from typing import Optional

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

user_repository = UserRepository(User)