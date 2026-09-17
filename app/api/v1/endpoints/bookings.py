from datetime import date

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUserDep, DbDep
from app.schemas.booking import BookingCreate, BookingRead
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