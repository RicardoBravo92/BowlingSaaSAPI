from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.utils import utcnow
from app.models.enums import BookingStatus

if TYPE_CHECKING:
    from app.models.infrastructure import Lane, PriceSlot
    from app.models.user import User

class BookingItem(SQLModel, table=True):
    """One booked cell (lane + price slot + hour) of a reservation.

    ``booking_date`` is denormalized from the parent Booking so that the unique
    constraint on (booking_date, lane_id, price_slot_id, start_hour) lives in a
    single table. It is the authoritative guard against double-booking: even if
    two concurrent requests both pass the in-memory availability check, only one
    row can be inserted. Services translate the resulting IntegrityError into
    HTTP 409.
    """
    __table_args__ = (
        UniqueConstraint(
            "booking_date", "lane_id", "price_slot_id", "start_hour",
            name="uq_booking_item_slot",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id")
    booking_date: date = Field(index=True)  # denormalized from Booking.booking_date
    lane_id: int = Field(foreign_key="lane.id")
    price_slot_id: int = Field(foreign_key="priceslot.id")
    start_hour: int = Field(default=0)  # The specific hour booked within the price slot (e.g. 14 for 14:00)

    booking: "Booking" = Relationship(back_populates="items")
    lane: "Lane" = Relationship(back_populates="items")
    price_slot: "PriceSlot" = Relationship(back_populates="items")

class Booking(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    booking_date: date
    total_price: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    status: BookingStatus = Field(default=BookingStatus.PENDING)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime | None = Field(default=None)  # 10-minute payment window (None = no expiration)

    user: "User" = Relationship(back_populates="bookings")
    items: list[BookingItem] = Relationship(
        back_populates="booking",
        sa_relationship_kwargs={"lazy": "selectin"}
    )