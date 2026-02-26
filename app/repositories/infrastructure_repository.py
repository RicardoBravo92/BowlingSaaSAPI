from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.infrastructure import Lane, Schedule, DayConfig, PriceSlot
from app.repositories.base_repository import BaseRepository

class InfrastructureRepository:
    """
    Infrastructure repository manages multiple models (Lane, Schedule, etc.),
    so it doesn't inherit from BaseRepository directly but uses similar patterns.
    """
    async def get_all_lanes(self, db: AsyncSession):
        result = await db.execute(select(Lane).order_by(Lane.number))
        return result.scalars().all()

    async def get_schedule_by_day(self, db: AsyncSession, day_of_week: int):
        """Finds which schedule applies today (0=Monday, 6=Sunday)"""
        result = await db.execute(
            select(Schedule)
            .join(DayConfig)
            .where(DayConfig.day_of_week == day_of_week)
        )
        return result.scalar_one_or_none()

    async def get_slots_by_schedule(self, db: AsyncSession, schedule_id: int):
        result = await db.execute(
            select(PriceSlot)
            .where(PriceSlot.schedule_id == schedule_id)
            .order_by(PriceSlot.start_time)
        )
        return result.scalars().all()

    async def calculate_total(self, db: AsyncSession, slot_ids: list[int]) -> float:
        """Sums the actual prices from the DB to prevent fraud from the frontend"""
        result = await db.execute(
            select(PriceSlot.price).where(PriceSlot.id.in_(slot_ids))
        )
        return sum(result.scalars().all())

    async def get_slots_by_ids(self, db: AsyncSession, slot_ids: list[int]):
        """Returns PriceSlot objects for the given IDs, ordered by start time"""
        result = await db.execute(
            select(PriceSlot)
            .where(PriceSlot.id.in_(slot_ids))
            .order_by(PriceSlot.start_time)
        )
        return result.scalars().all()

infrastructure_repo = InfrastructureRepository()