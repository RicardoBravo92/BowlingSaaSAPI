from datetime import date

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUserDep, DbDep
from app.models.enums import BookingStatus
from app.schemas.booking import BookingCreate, BookingDetail, BookingRead
from app.schemas.infrastructure import AvailabilityGrid
from app.services.booking_service import booking_service
from app.services.infrastructure_service import infrastructure_service

router = APIRouter()


@router.get("/availability", response_model=list[AvailabilityGrid])
async def get_grid(booking_date: date, db: DbDep):
    """Returns the availability grid of all lanes and slots for a given date"""
    return await infrastructure_service.get_grid_availability(db, booking_date)


@router.post("/reserve", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(payload: BookingCreate, db: DbDep, current_user: CurrentUserDep):
    """Creates a pending reservation (10-minute block)"""
    return await booking_service.create_reservation(db, current_user.id, payload)


@router.get("/my", response_model=list[BookingDetail])
async def get_my_bookings(
    db: DbDep,
    current_user: CurrentUserDep,
    status: BookingStatus | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
):
    """Returns all reservations of the authenticated user, optionally filtered."""
    return await booking_service.get_user_bookings(
        db, current_user.id, status=status, from_date=from_date, to_date=to_date
    )


@router.delete("/{booking_id}", response_model=BookingDetail)
async def cancel_booking(booking_id: int, db: DbDep, current_user: CurrentUserDep):
    """Cancels a pending reservation owned by the authenticated user."""
    return await booking_service.cancel_reservation(db, booking_id, current_user.id)