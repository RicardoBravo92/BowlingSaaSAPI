from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.booking import Booking, BookingItem
from app.models.enums import BookingStatus
from sqlalchemy.orm import selectinload
from app.repositories.base_repository import BaseRepository

class BookingRepository(BaseRepository[Booking]):
    async def get_with_details(self, db: AsyncSession, booking_id: int) -> Booking:
        """Fetches a booking with its user and items (including lane info) pre-loaded."""
        stmt = (
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.items).selectinload(BookingItem.lane)
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    async def get_occupied_slots(self, db: AsyncSession, booking_date: date):
        """
        Returns a set of (lane_id, slot_id) that are NOT available.
        Considers:
        1. PAID reservations.
        2. PENDING reservations that have not yet expired.
        """
        now = datetime.utcnow()
        
        stmt = (
            select(BookingItem.lane_id, BookingItem.price_slot_id)
            .join(Booking)
            .where(
                and_(
                    Booking.booking_date == booking_date,
                    or_(
                        Booking.status == BookingStatus.PAID,
                        and_(
                            Booking.status == BookingStatus.PENDING,
                            Booking.expires_at > now
                        )
                    )
                )
            )
        )
        
        result = await db.execute(stmt)
        # Convert to a set of tuples for fast O(1) lookup in the Service
        return {(row.lane_id, row.price_slot_id) for row in result.all()}

booking_repo = BookingRepository(Booking)