from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.core.utils import utcnow
from app.models.enums import BookingStatus

if TYPE_CHECKING:
    from app.models.infrastructure import Lane, PriceSlot
    from app.models.user import User

class BookingItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id")
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
    total_price: float
    status: BookingStatus = Field(default=BookingStatus.PENDING)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime # For the 10-minute slot lock
    
    user: "User" = Relationship(back_populates="bookings")
    items: list[BookingItem] = Relationship(
        back_populates="booking",
        sa_relationship_kwargs={"lazy": "selectin"}
    )