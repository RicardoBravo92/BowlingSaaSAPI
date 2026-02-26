from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.infrastructure_repository import infrastructure_repo
from app.repositories.booking_repository import booking_repo

class InfrastructureService:
    async def get_grid_availability(self, db: AsyncSession, booking_date: date):
        # 1. Get the price schedule for the day of the week
        weekday = booking_date.weekday()
        schedule = await infrastructure_repo.get_schedule_by_day(db, weekday)
        
        if not schedule:
            return []

        # 2. Get lanes and slots for that schedule
        lanes = await infrastructure_repo.get_all_lanes(db)
        slots = await infrastructure_repo.get_slots_by_schedule(db, schedule.id)
        
        # 3. Get already occupied cells (Paid or non-expired Pending)
        occupied = await booking_repo.get_occupied_slots(db, booking_date)
        # 'occupied' will be a set of tuples {(lane_id, slot_id), ...}

        # 4. Format for the frontend
        grid = []
        for lane in lanes:
            lane_data = {
                "lane_id": lane.id,
                "lane_number": lane.number,
                "type": lane.type,
                "slots": [
                    {
                        "slot_id": s.id,
                        "time": f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}",
                        "price": s.price,
                        "available": (lane.id, s.id) not in occupied
                    } for s in slots
                ]
            }
            grid.append(lane_data)
        return grid

infrastructure_service = InfrastructureService()