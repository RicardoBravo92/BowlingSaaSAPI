import asyncio
from sqlmodel import select
from app.core.database import AsyncSessionLocal
from app.models.infrastructure import Lane, Schedule, PriceSlot, DayConfig
from app.models.enums import LaneType
from datetime import time

async def seed_infra():
    async with AsyncSessionLocal() as db:
        print("Creating Lanes...")
        # Create Lanes
        lane1 = Lane(number="1", type=LaneType.NORMAL)
        lane2 = Lane(number="2", type=LaneType.VIP)
        lane3 = Lane(number="3", type=LaneType.KIDS)
        db.add_all([lane1, lane2, lane3])
        await db.commit()

        print("Creating Schedules...")
        # Create Schedule
        sched1 = Schedule(name="General")
        sched2 = Schedule(name="Fin de Semana")
        db.add_all([sched1, sched2])
        await db.commit()
        await db.refresh(sched1)
        await db.refresh(sched2)

        print("Creating Price Slots...")
        # Create Slots
        slot1 = PriceSlot(schedule_id=sched1.id, start_time=time(10,0), end_time=time(18,0), price=15.0)
        slot2 = PriceSlot(schedule_id=sched1.id, start_time=time(18,0), end_time=time(22,0), price=25.0)
        
        slot3 = PriceSlot(schedule_id=sched2.id, start_time=time(10,0), end_time=time(14,0), price=20.0)
        slot4 = PriceSlot(schedule_id=sched2.id, start_time=time(14,0), end_time=time(23,0), price=35.0)
        db.add_all([slot1, slot2, slot3, slot4])
        await db.commit()

        print("Assigning Schedules to Days...")
        # Assign Days
        # Friday (4), Saturday (5), Sunday (6) -> Fin de Semana
        # Monday (0) to Thursday (3) -> General
        result = await db.execute(select(DayConfig))
        configs = result.scalars().all()
        for dc in configs:
            if dc.day_of_week in [4, 5, 6]:
                dc.schedule_id = sched2.id
            else:
                dc.schedule_id = sched1.id
            db.add(dc)
        
        # If configs don't exist yet, create them:
        if not configs:
            for d in range(7):
                sid = sched2.id if d in [4, 5, 6] else sched1.id
                dc = DayConfig(day_of_week=d, schedule_id=sid)
                db.add(dc)

        await db.commit()
        print("Infrastructure Seeding Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(seed_infra())
