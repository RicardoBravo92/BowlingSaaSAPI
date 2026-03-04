from typing import Optional, List
from pydantic import BaseModel
from datetime import time
from app.models.enums import LaneType

class PriceSlotRead(BaseModel):
    id: int
    start_time: time
    end_time: time
    price: float

    class Config:
        from_attributes = True

class LaneRead(BaseModel):
    id: int
    number: str
    type: LaneType

    class Config:
        from_attributes = True

class LaneCreate(BaseModel):
    number: str
    type: LaneType = LaneType.NORMAL

class LaneUpdate(BaseModel):
    number: Optional[str] = None
    type: Optional[LaneType] = None

class PriceSlotUpdate(BaseModel):
    price: float

class ScheduleRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class ScheduleCreate(BaseModel):
    name: str

class SlotInfo(BaseModel):
    slot_id: int
    time: str
    price: float
    available: bool

# This schema is used for the frontend Availability Grid
class AvailabilityGrid(BaseModel):
    lane_id: int
    lane_number: str
    type: LaneType
    slots: List[SlotInfo]