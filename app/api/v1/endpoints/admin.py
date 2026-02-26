from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.api.dependencies import get_current_active_cashier, get_current_active_owner
from app.services.booking_service import booking_service
from app.services.user_service import user_service
from app.schemas.user import UserRead, UserUpdate
from app.repositories.user_repository import user_repository
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# --- BOOKING MANAGEMENT ---

@router.post("/confirm-payment/{booking_id}")
async def confirm_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    cashier = Depends(get_current_active_cashier)
):
    """Confirm that the user has paid (in-person or manual)"""
    return await booking_service.confirm_payment(db, booking_id)

# --- USER MANAGEMENT (OWNER ONLY) ---

@router.get("/users", response_model=List[UserRead])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    owner = Depends(get_current_active_owner)
):
    """List all registered users (Pagination supported)"""
    return await user_repository.get_multi(db, skip=skip, limit=limit)

@router.get("/users/{user_id}", response_model=UserRead)
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    owner = Depends(get_current_active_owner)
):
    """Get details of a specific user"""
    user = await user_repository.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user_role(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    owner = Depends(get_current_active_owner)
):
    """
    Update user information, including roles.
    Used by owners to promote users to 'cashier' or 'owner'.
    """
    logger.info(f"Owner {owner.id} is updating user {user_id}")
    db_user = await user_repository.get(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return await user_repository.update(db, db_obj=db_user, obj_in=user_in)

# --- REPORTS ---

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    owner = Depends(get_current_active_owner)
):
    """Sales and occupancy reports (Owner only)"""
    # TODO: Implement analytics service
    return {
        "summary": "Report system status: Initialized",
        "notice": "Analytical data will be available once the booking history grows."
    }