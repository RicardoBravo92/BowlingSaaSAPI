from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import BookingStatus


# What the frontend sends when the user clicks "Reserve"
class BookingCreate(BaseModel):
    booking_date: date
    slot_keys: list[str]  # format: "{lane_id}:{price_slot_id}:{start_hour}" e.g., ["1:3:14", "2:3:15"]


class BookingMove(BaseModel):
    slot_keys: list[str]  # new target cells for the same booking date

class BookingAssign(BaseModel):
    """Staff assigns a lane to a user as a gift (ASSIGNED status, no charge)."""
    user_id: int
    booking_date: date
    slot_keys: list[str]  # format: "{lane_id}:{price_slot_id}:{start_hour}"

class BookingItemRead(BaseModel):
    lane_id: int
    price_slot_id: int
    start_hour: int

class BookingRead(BaseModel):
    id: int
    user_id: int
    booking_date: date
    total_price: float
    status: BookingStatus
    expires_at: datetime
    items: list[BookingItemRead]

    model_config = ConfigDict(from_attributes=True)


class BookingItemDetail(BaseModel):
    lane_id: int
    lane_number: str
    start_hour: int


class BookingDetail(BaseModel):
    id: int
    booking_date: date
    total_price: float
    status: BookingStatus
    expires_at: datetime
    created_at: datetime
    items: list[BookingItemDetail]


class AdminBookingDetail(BaseModel):
    """Booking detail for staff views, including the client info."""
    id: int
    user_id: int
    user_full_name: str
    user_email: str
    booking_date: date
    total_price: float
    status: BookingStatus
    expires_at: datetime
    created_at: datetime
    items: list[BookingItemDetail]

    model_config = ConfigDict(from_attributes=True)
