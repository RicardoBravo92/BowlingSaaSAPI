from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils import utcnow
from app.models.booking import Booking, BookingItem
from app.models.enums import BookingStatus
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
        Returns a set of (lane_id, slot_id, start_hour) that are NOT available.
        Considers:
        1. PAID reservations.
        2. PENDING reservations that have not yet expired.
        """
        now = utcnow()

        stmt = (
            select(BookingItem.lane_id, BookingItem.price_slot_id, BookingItem.start_hour)
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
        # Convert to a set of 3-tuples for fast O(1) lookup in the Service
        return {(row.lane_id, row.price_slot_id, row.start_hour) for row in result.all()}

    async def get_expired_pending_bookings(self, db: AsyncSession):
        """Fetches all PENDING bookings where expires_at < now."""
        now = utcnow()
        stmt = select(Booking).where(
            and_(
                Booking.status == BookingStatus.PENDING,
                Booking.expires_at < now
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

booking_repo = BookingRepository(Booking)