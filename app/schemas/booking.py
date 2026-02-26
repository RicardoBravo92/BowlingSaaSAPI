from pydantic import BaseModel
from datetime import date, datetime
from typing import List
from app.models.enums import BookingStatus

# What the frontend sends when the user clicks "Pay"
class BookingCreate(BaseModel):
    booking_date: date
    # We send a list of PriceSlot IDs
    selected_slots: List[int] # Selected PriceSlot IDs
    lane_id: int

class BookingItemRead(BaseModel):
    lane_id: int
    price_slot_id: int

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