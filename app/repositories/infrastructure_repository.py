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

    async def get_lanes_by_ids(self, db: AsyncSession, lane_ids: list[int]):
        """Returns Lane objects for the given IDs"""
        result = await db.execute(select(Lane).where(Lane.id.in_(lane_ids)))
        return result.scalars().all()

    async def get_schedule_by_day(self, db: AsyncSession, day_of_week: int):
        """Finds which schedule applies today (0=Monday, 6=Sunday)"""
        result = await db.execute(
            select(Schedule)
            .join(DayConfig)
            .where(DayConfig.day_of_week == day_of_week)
        )
        return result.scalar_one_or_none()

    async def get_all_schedules(self, db: AsyncSession):
        result = await db.execute(select(Schedule).order_by(Schedule.id))
        return result.scalars().all()

    async def create_schedule(self, db: AsyncSession, schedule: Schedule):
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    async def get_schedule(self, db: AsyncSession, schedule_id: int):
        result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
        return result.scalar_one_or_none()

    async def delete_schedule(self, db: AsyncSession, schedule: Schedule):
        await db.delete(schedule)
        await db.commit()
        return True

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

    async def get_lane(self, db: AsyncSession, lane_id: int):
        result = await db.execute(select(Lane).where(Lane.id == lane_id))
        return result.scalar_one_or_none()

    async def create_lane(self, db: AsyncSession, lane: Lane):
        db.add(lane)
        await db.commit()
        await db.refresh(lane)
        return lane

    async def delete_lane(self, db: AsyncSession, lane: Lane):
        await db.delete(lane)
        await db.commit()
        return True

    async def update_lane(self, db: AsyncSession, lane: Lane, lane_in: dict):
        for key, value in lane_in.items():
            if value is not None:
                setattr(lane, key, value)
        await db.commit()
        await db.refresh(lane)
        return lane

    async def get_slot(self, db: AsyncSession, slot_id: int):
        result = await db.execute(select(PriceSlot).where(PriceSlot.id == slot_id))
        return result.scalar_one_or_none()

    async def update_slot(self, db: AsyncSession, slot: PriceSlot, slot_in: dict):
        for key, value in slot_in.items():
            if value is not None:
                setattr(slot, key, value)
        await db.commit()
        await db.refresh(slot)
        return slot

    async def create_slot(self, db: AsyncSession, slot: PriceSlot):
        db.add(slot)
        await db.commit()
        await db.refresh(slot)
        return slot

    async def delete_slot(self, db: AsyncSession, slot: PriceSlot):
        await db.delete(slot)
        await db.commit()
        return True

    async def get_all_day_configs(self, db: AsyncSession):
        result = await db.execute(select(DayConfig).order_by(DayConfig.day_of_week))
        return result.scalars().all()

    async def update_day_config(self, db: AsyncSession, day_config: DayConfig):
        db.add(day_config)
        await db.commit()
        await db.refresh(day_config)
        return day_config

infrastructure_repo = InfrastructureRepository()