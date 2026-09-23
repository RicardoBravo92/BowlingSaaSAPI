from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.utils import localnow, utcnow
from app.repositories.infrastructure_repository import infrastructure_repo
from app.repositories.booking_repository import booking_repo
from app.models.infrastructure import Lane, MaintenanceRecord, Schedule, PriceSlot, DayConfig
from app.schemas.infrastructure import LaneCreate, LaneUpdate, MaintenanceRecordRead, PriceSlotUpdate, ScheduleCreate, PriceSlotCreate, DayConfigRead, DayConfigUpdate

class InfrastructureService:
    async def get_grid_availability(self, db: AsyncSession, booking_date: date):
        # 1. Get the price schedule for the day of the week
        weekday = booking_date.weekday()
        schedule = await infrastructure_repo.get_schedule_by_day(db, weekday)

        if not schedule:
            return []

        # 2. Get lanes and slots for that schedule (only active lanes are bookable)
        lanes = await infrastructure_repo.get_all_lanes(db, active_only=True)
        slots = await infrastructure_repo.get_slots_by_schedule(db, schedule.id)

        # 3. Get already occupied cells per (lane_id, slot_id, start_hour)
        occupied = await booking_repo.get_occupied_slots(db, booking_date)
        # occupied is a set of tuples {(lane_id, slot_id, start_hour), ...}

        # Past hours (venue local time) are never available for booking
        now = localnow()
        is_past_date = booking_date < now.date()
        is_today = booking_date == now.date()

        # 4. Expand each PriceSlot into individual 1-hour blocks
        grid = []
        for lane in lanes:
            hourly_slots = []
            base_price = lane.type.value == "PREMIUM"
            for s in slots:
                # Iterate hour by hour within the slot range
                start_h = s.start_time.hour
                end_h = s.end_time.hour
                for h in range(start_h, end_h):
                    price = s.premium_price if base_price else s.price
                    is_past = is_past_date or (is_today and h <= now.hour)
                    is_available = not is_past and (lane.id, s.id, h) not in occupied
                    hourly_slots.append({
                        "slot_id": s.id,
                        "slot_key": f"{lane.id}:{s.id}:{h}",   # unique key per hour, includes lane_id
                        "time": f"{h:02d}:00",
                        "price": price,
                        "available": is_available,
                    })
            grid.append({
                "lane_id": lane.id,
                "lane_number": lane.number,
                "type": lane.type,
                "slots": hourly_slots,
            })
        return grid

    async def create_lane(self, db: AsyncSession, lane_in: LaneCreate):
        new_lane = Lane(number=lane_in.number, type=lane_in.type)
        return await infrastructure_repo.create_lane(db, new_lane)

    async def delete_lane(self, db: AsyncSession, lane_id: int):
        lane = await infrastructure_repo.get_lane(db, lane_id)
        if not lane:
            raise HTTPException(status_code=404, detail="Lane not found")
        return await infrastructure_repo.delete_lane(db, lane)

    async def update_lane(self, db: AsyncSession, lane_id: int, lane_in: LaneUpdate, changed_by: int | None = None):
        lane = await infrastructure_repo.get_lane(db, lane_id)
        if not lane:
            raise HTTPException(status_code=404, detail="Lane not found")
        update_data = lane_in.model_dump(exclude_unset=True)
        was_active = lane.is_active
        maintenance_reason = update_data.pop("maintenance_reason", None)
        updated = await infrastructure_repo.update_lane(db, lane, update_data)

        # Track maintenance episodes: disabling opens a record, reactivating closes it.
        if "is_active" in update_data and update_data["is_active"] != was_active:
            if update_data["is_active"] is False:
                open_record = await infrastructure_repo.get_open_maintenance(db, lane_id)
                if not open_record:
                    open_record = MaintenanceRecord(
                        lane_id=lane_id,
                        reason=maintenance_reason,
                        changed_by=changed_by,
                    )
                    open_record = await infrastructure_repo.add_maintenance(db, open_record)
            else:
                open_record = await infrastructure_repo.get_open_maintenance(db, lane_id)
                if open_record and open_record.ended_at is None:
                    open_record.ended_at = utcnow()
                    open_record = await infrastructure_repo.close_maintenance(db, open_record)

        return updated

    async def get_maintenance_history(
        self,
        db: AsyncSession,
        lane_id: int | None = None,
    ) -> list[MaintenanceRecordRead]:
        """Returns the maintenance history, optionally filtered by lane."""
        records = await infrastructure_repo.get_all_maintenance(db, lane_id)
        lanes = await infrastructure_repo.get_all_lanes(db)
        lanes_by_id = {lane.id: lane for lane in lanes}
        return [
            MaintenanceRecordRead(
                id=record.id,
                lane_id=record.lane_id,
                lane_number=lanes_by_id[record.lane_id].number if record.lane_id in lanes_by_id else str(record.lane_id),
                reason=record.reason,
                started_at=record.started_at,
                ended_at=record.ended_at,
                changed_by=record.changed_by,
            )
            for record in records
        ]

    async def update_slot(self, db: AsyncSession, slot_id: int, slot_in: PriceSlotUpdate):
        slot = await infrastructure_repo.get_slot(db, slot_id)
        if not slot:
            raise HTTPException(status_code=404, detail="Price slot not found")
        update_data = slot_in.model_dump(exclude_unset=True)
        return await infrastructure_repo.update_slot(db, slot, update_data)

    async def get_all_schedules(self, db: AsyncSession):
        return await infrastructure_repo.get_all_schedules(db)

    async def create_schedule(self, db: AsyncSession, schedule_in: ScheduleCreate):
        new_schedule = Schedule(name=schedule_in.name)
        return await infrastructure_repo.create_schedule(db, new_schedule)

    async def delete_schedule(self, db: AsyncSession, schedule_id: int):
        schedule = await infrastructure_repo.get_schedule(db, schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return await infrastructure_repo.delete_schedule(db, schedule)

    async def create_slot(self, db: AsyncSession, slot_in: PriceSlotCreate):
        new_slot = PriceSlot(
            start_time=slot_in.start_time,
            end_time=slot_in.end_time,
            price=slot_in.price,
            premium_price=slot_in.premium_price,
            schedule_id=slot_in.schedule_id
        )
        return await infrastructure_repo.create_slot(db, new_slot)

    async def delete_slot(self, db: AsyncSession, slot_id: int):
        slot = await infrastructure_repo.get_slot(db, slot_id)
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        return await infrastructure_repo.delete_slot(db, slot)

    async def get_day_configs(self, db: AsyncSession):
        return await infrastructure_repo.get_all_day_configs(db)

    async def update_day_config(self, db: AsyncSession, day_of_week: int, config_in: DayConfigUpdate):
        # Days are unique 0-6. We use DayConfig as mapping
        from sqlalchemy import select
        result = await db.execute(select(DayConfig).where(DayConfig.day_of_week == day_of_week))
        day_config = result.scalar_one_or_none()
        
        if not day_config:
            day_config = DayConfig(day_of_week=day_of_week, schedule_id=config_in.schedule_id)
        else:
            day_config.schedule_id = config_in.schedule_id
            
        return await infrastructure_repo.update_day_config(db, day_config)

infrastructure_service = InfrastructureService()