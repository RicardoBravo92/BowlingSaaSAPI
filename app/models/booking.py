from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums import BookingStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.infrastructure import Lane, PriceSlot

class BookingItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id")
    lane_id: int = Field(foreign_key="lane.id")
    price_slot_id: int = Field(foreign_key="priceslot.id")
    
    booking: "Booking" = Relationship(back_populates="items")
    lane: "Lane" = Relationship(back_populates="items")
    price_slot: "PriceSlot" = Relationship(back_populates="items")

class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    booking_date: date
    total_price: float
    status: BookingStatus = Field(default=BookingStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime # For the 10-minute slot lock
    
    user: "User" = Relationship(back_populates="bookings")
    items: List[BookingItem] = Relationship(back_populates="booking")