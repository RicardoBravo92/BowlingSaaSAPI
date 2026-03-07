from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.api.dependencies import get_db, get_current_active_owner
from app.models.user import User
from app.services.infrastructure_service import infrastructure_service
from app.schemas.infrastructure import (
    LaneRead, LaneCreate, LaneUpdate, PriceSlotUpdate, PriceSlotRead,
    ScheduleRead, ScheduleCreate, DayConfigRead, DayConfigUpdate,
    PriceSlotCreate
)

router = APIRouter()

# --- LANES ---

@router.get("/lanes", response_model=List[LaneRead])
async def get_lanes(
    db: AsyncSession = Depends(get_db)
):
    """List all bowling lanes"""
    from app.repositories.infrastructure_repository import infrastructure_repo
    return await infrastructure_repo.get_all_lanes(db)

@router.post("/lanes", response_model=LaneRead, status_code=status.HTTP_201_CREATED)
async def create_lane(
    lane_in: LaneCreate,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Create a new bowling lane (Owner Only)"""
    return await infrastructure_service.create_lane(db, lane_in)

@router.delete("/lanes/{lane_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lane(
    lane_id: int,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Delete a bowling lane (Owner Only)"""
    await infrastructure_service.delete_lane(db, lane_id)
    return None

@router.patch("/lanes/{lane_id}", response_model=LaneRead)
async def update_lane(
    lane_id: int,
    lane_in: LaneUpdate,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Update lane details (Owner Only)"""
    return await infrastructure_service.update_lane(db, lane_id, lane_in)


# --- PRICE SLOTS ---

@router.get("/slots/schedule/{schedule_id}", response_model=List[PriceSlotRead])
async def get_slots_by_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """List all slots for a specific schedule"""
    from app.repositories.infrastructure_repository import infrastructure_repo
    return await infrastructure_repo.get_slots_by_schedule(db, schedule_id)

@router.post("/slots", response_model=PriceSlotRead, status_code=status.HTTP_201_CREATED)
async def create_slot(
    slot_in: PriceSlotCreate,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Create a new time slot for a schedule (Owner Only)"""
    return await infrastructure_service.create_slot(db, slot_in)

@router.patch("/slots/{slot_id}", response_model=PriceSlotRead)
async def update_slot(
    slot_id: int,
    slot_in: PriceSlotUpdate,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Update a specific time slot (Owner Only)"""
    return await infrastructure_service.update_slot(db, slot_id, slot_in)

@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Delete a price slot (Owner Only)"""
    await infrastructure_service.delete_slot(db, slot_id)
    return None

# --- SCHEDULES ---

@router.get("/schedules", response_model=List[ScheduleRead])
async def get_schedules(
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """List all pricing schedules"""
    return await infrastructure_service.get_all_schedules(db)

@router.post("/schedules", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_in: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Create a new pricing schedule"""
    return await infrastructure_service.create_schedule(db, schedule_in)

@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Delete a schedule"""
    await infrastructure_service.delete_schedule(db, schedule_id)
    return None

# --- DAY CONFIGS ---

@router.get("/days", response_model=List[DayConfigRead])
async def get_day_configs(
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Get mapping of days of week to schedules"""
    return await infrastructure_service.get_day_configs(db)

@router.put("/days/{day_of_week}", response_model=DayConfigRead)
async def update_day_config(
    day_of_week: int,
    config_in: DayConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner)
):
    """Update which schedule applies to a specific day (0=Mon, 6=Sun)"""
    return await infrastructure_service.update_day_config(db, day_of_week, config_in)