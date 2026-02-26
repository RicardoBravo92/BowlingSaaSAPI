from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.booking_service import booking_service
from app.services.infrastructure_service import infrastructure_service
from app.schemas.booking import BookingCreate, BookingRead
from app.models.user import User

router = APIRouter()

@router.get("/availability")
async def get_grid(
    booking_date: date, 
    db: AsyncSession = Depends(get_db)
):
    """Returns the availability grid of all lanes and slots for a given date"""
    return await infrastructure_service.get_grid_availability(db, booking_date)

@router.post("/reserve", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a pending reservation (10-minute block)"""
    return await booking_service.create_reservation(db, current_user.id, payload)