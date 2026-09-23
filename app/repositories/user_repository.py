from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from typing import Optional

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def search(self, db: AsyncSession, query: str, limit: int = 10) -> list[User]:
        """Search users by full name or email (case-insensitive partial match)."""
        q = f"%{query.lower()}%"
        stmt = (
            select(User)
            .where(
                or_(
                    func.lower(User.full_name).like(q),
                    func.lower(User.email).like(q)
                )
            )
            .order_by(User.full_name)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


user_repository = UserRepository(User)