from pydantic import BaseModel
from datetime import date, datetime
from typing import List
from app.models.enums import BookingStatus

# What the frontend sends when the user clicks "Reserve"
class BookingCreate(BaseModel):
    booking_date: date
    slot_keys: List[str]  # format: "{lane_id}:{price_slot_id}:{start_hour}" e.g., ["1:3:14", "2:3:15"]

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
    items: List[BookingItemRead]

    class Config:
        from_attributes = True
