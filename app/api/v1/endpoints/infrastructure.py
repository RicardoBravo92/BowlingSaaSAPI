
from fastapi import APIRouter, status

from app.api.dependencies import CurrentActiveOwnerDep, DbDep
from app.repositories.infrastructure_repository import infrastructure_repo
from app.schemas.infrastructure import (
    DayConfigRead,
    DayConfigUpdate,
    LaneCreate,
    LaneRead,
    LaneUpdate,
    PriceSlotCreate,
    PriceSlotRead,
    PriceSlotUpdate,
    ScheduleCreate,
    ScheduleRead,
)
from app.services.infrastructure_service import infrastructure_service

router = APIRouter()

# --- LANES ---

@router.get("/lanes", response_model=list[LaneRead])
async def get_lanes(db: DbDep):
    """List all bowling lanes"""
    return await infrastructure_repo.get_all_lanes(db)

@router.post("/lanes", response_model=LaneRead, status_code=status.HTTP_201_CREATED)
async def create_lane(
    lane_in: LaneCreate,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Create a new bowling lane (Owner Only)"""
    return await infrastructure_service.create_lane(db, lane_in)

@router.delete("/lanes/{lane_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lane(
    lane_id: int,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Delete a bowling lane (Owner Only)"""
    await infrastructure_service.delete_lane(db, lane_id)

@router.patch("/lanes/{lane_id}", response_model=LaneRead)
async def update_lane(
    lane_id: int,
    lane_in: LaneUpdate,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Update lane details (Owner Only)"""
    return await infrastructure_service.update_lane(db, lane_id, lane_in)


# --- PRICE SLOTS ---

@router.get("/slots/schedule/{schedule_id}", response_model=list[PriceSlotRead])
async def get_slots_by_schedule(
    schedule_id: int,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """List all slots for a specific schedule"""
    return await infrastructure_repo.get_slots_by_schedule(db, schedule_id)

@router.post("/slots", response_model=PriceSlotRead, status_code=status.HTTP_201_CREATED)
async def create_slot(
    slot_in: PriceSlotCreate,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Create a new time slot for a schedule (Owner Only)"""
    return await infrastructure_service.create_slot(db, slot_in)

@router.patch("/slots/{slot_id}", response_model=PriceSlotRead)
async def update_slot(
    slot_id: int,
    slot_in: PriceSlotUpdate,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Update a specific time slot (Owner Only)"""
    return await infrastructure_service.update_slot(db, slot_id, slot_in)

@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: int,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Delete a price slot (Owner Only)"""
    await infrastructure_service.delete_slot(db, slot_id)

# --- SCHEDULES ---

@router.get("/schedules", response_model=list[ScheduleRead])
async def get_schedules(
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """List all pricing schedules"""
    return await infrastructure_service.get_all_schedules(db)

@router.post("/schedules", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_in: ScheduleCreate,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Create a new pricing schedule"""
    return await infrastructure_service.create_schedule(db, schedule_in)

@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Delete a schedule"""
    await infrastructure_service.delete_schedule(db, schedule_id)

# --- DAY CONFIGS ---

@router.get("/days", response_model=list[DayConfigRead])
async def get_day_configs(
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Get mapping of days of week to schedules"""
    return await infrastructure_service.get_day_configs(db)

@router.put("/days/{day_of_week}", response_model=DayConfigRead)
async def update_day_config(
    day_of_week: int,
    config_in: DayConfigUpdate,
    db: DbDep,
    current_owner: CurrentActiveOwnerDep,
):
    """Update which schedule applies to a specific day (0=Mon, 6=Sun)"""
    return await infrastructure_service.update_day_config(db, day_of_week, config_in)