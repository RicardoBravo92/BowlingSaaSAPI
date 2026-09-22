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

    async def get_by_id_and_user(self, db: AsyncSession, booking_id: int, user_id: int) -> Booking | None:
        """Fetches a single booking only if it belongs to the given user."""
        stmt = (
            select(Booking)
            .where(and_(Booking.id == booking_id, Booking.user_id == user_id))
            .options(selectinload(Booking.items).selectinload(BookingItem.lane))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        db: AsyncSession,
        *,
        status: BookingStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        """Fetches all bookings with user, items and lane info pre-loaded, newest first."""
        filters = []
        if status is not None:
            filters.append(Booking.status == status)
        if from_date is not None:
            filters.append(Booking.booking_date >= from_date)
        if to_date is not None:
            filters.append(Booking.booking_date <= to_date)

        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.items).selectinload(BookingItem.lane),
            )
            .order_by(Booking.booking_date.desc(), Booking.id.desc())
        )
        if filters:
            stmt = stmt.where(and_(*filters))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        status: BookingStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        """Fetches all bookings for a user, with items and lane info pre-loaded."""
        filters = [Booking.user_id == user_id]
        if status is not None:
            filters.append(Booking.status == status)
        if from_date is not None:
            filters.append(Booking.booking_date >= from_date)
        if to_date is not None:
            filters.append(Booking.booking_date <= to_date)

        stmt = (
            select(Booking)
            .where(and_(*filters))
            .options(selectinload(Booking.items).selectinload(BookingItem.lane))
            .order_by(Booking.booking_date.desc(), Booking.id.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

booking_repo = BookingRepository(Booking)