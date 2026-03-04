from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.api.dependencies import get_db, get_current_active_owner
from app.models.user import User
from app.services.infrastructure_service import infrastructure_service
from app.schemas.infrastructure import LaneRead, LaneCreate, PriceSlotUpdate, PriceSlotRead

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

# --- PRICE SLOTS ---

@router.patch("/slots/{slot_id}", response_model=PriceSlotRead)
async def update_slot_price(
    slot_id: int,
    slot_in: PriceSlotUpdate,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner) 
):
    """Update the price of a specific time slot (Owner Only)"""
    return await infrastructure_service.update_slot_price(db, slot_id, slot_in)