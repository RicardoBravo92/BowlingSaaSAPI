from pydantic import BaseModel
from datetime import time
from app.models.enums import LaneType

class PriceSlotRead(BaseModel):
    id: int
    start_time: time
    end_time: time
    price: float

class LaneRead(BaseModel):
    id: int
    number: str
    type: LaneType

# This schema is used for the frontend Availability Grid
class AvailabilityGrid(BaseModel):
    lane_id: int
    lane_number: str
    lane_type: LaneType
    slots: list[dict] # {slot_id, time, price, available}