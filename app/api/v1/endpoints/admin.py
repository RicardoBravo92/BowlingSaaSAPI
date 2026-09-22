from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.api.dependencies import (
    CurrentActiveCashierDep,
    CurrentActiveOwnerDep,
    DbDep,
)
from app.core.logging_config import get_logger
from app.models.enums import BookingStatus
from app.repositories.user_repository import user_repository
from app.schemas.analytics import StatsRead
from app.schemas.booking import AdminBookingDetail, BookingMove, BookingRead
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead, UserUpdate
from app.services.analytics_service import analytics_service
from app.services.booking_service import booking_service

logger = get_logger(__name__)
router = APIRouter()

# --- BOOKING MANAGEMENT ---

@router.post(
    "/confirm-payment/{booking_id}",
    response_model=BookingRead,
    status_code=status.HTTP_200_OK,
)
async def confirm_booking(
    booking_id: int,
    db: DbDep,
    cashier: CurrentActiveCashierDep,
    background_tasks: BackgroundTasks,
):
    """Confirm that the user has paid (in-person or manual)"""
    return await booking_service.confirm_payment(db, booking_id, background_tasks=background_tasks)


@router.get("/bookings", response_model=list[AdminBookingDetail])
async def list_bookings(
    db: DbDep,
    staff: CurrentActiveCashierDep,
    status: BookingStatus | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
):
    """List all reservations with the client info (Cashier, Manager or Owner)"""
    return await booking_service.get_all_bookings(
        db, status=status, from_date=from_date, to_date=to_date
    )


@router.delete("/bookings/{booking_id}", response_model=AdminBookingDetail)
async def cancel_booking(
    booking_id: int,
    db: DbDep,
    staff: CurrentActiveCashierDep,
):
    """Cancel any reservation (Cashier, Manager or Owner)"""
    return await booking_service.cancel_booking(db, booking_id)


@router.post("/bookings/{booking_id}/move", response_model=AdminBookingDetail)
async def move_booking(
    booking_id: int,
    payload: BookingMove,
    db: DbDep,
    staff: CurrentActiveCashierDep,
):
    """Move a reservation to different lanes/times (e.g. damaged lane)"""
    return await booking_service.move_booking(db, booking_id, payload.slot_keys)

# --- USER MANAGEMENT (OWNER ONLY) ---

@router.get("/users", response_model=list[UserRead])
async def list_users(
    db: DbDep,
    owner: CurrentActiveOwnerDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    """List all registered users (Pagination supported)"""
    return await user_repository.get_multi(db, skip=skip, limit=limit)

@router.get("/users/{user_id}", response_model=UserRead)
async def get_user_detail(
    user_id: int,
    db: DbDep,
    owner: CurrentActiveOwnerDep,
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
    db: DbDep,
    owner: CurrentActiveOwnerDep,
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

# --- MAINTENANCE ---

@router.post("/maintenance/cleanup-bookings", response_model=MessageResponse)
async def cleanup_bookings(
    db: DbDep,
    owner: CurrentActiveOwnerDep,
):
    """Manually trigger the cancellation of expired pending bookings"""
    count = await booking_service.cleanup_expired_bookings(db)
    return MessageResponse(
        message=f"Cleanup completed. {count} bookings cancelled."
    )

# --- REPORTS ---

@router.get("/stats", response_model=StatsRead)
async def get_stats(
    db: DbDep,
    owner: CurrentActiveOwnerDep,
):
    """Business intelligence metrics for owners"""
    summary = await analytics_service.get_summary_stats(db)
    history = await analytics_service.get_occupancy_report(db, days=30)

    return {
        "summary": summary,
        "daily_history": history,
        "period": "Last 30 days"
    }