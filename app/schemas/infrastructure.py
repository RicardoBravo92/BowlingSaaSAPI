from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import time
from app.models.enums import LaneType

class PriceSlotRead(BaseModel):
    id: int
    start_time: time
    end_time: time
    price: float
    premium_price: float

    class Config:
        from_attributes = True

class PriceSlotCreate(BaseModel):
    start_time: time
    end_time: time
    price: float = Field(ge=0.0)
    premium_price: float = Field(default=0.0, ge=0.0)
    schedule_id: int

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
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    premium_price: Optional[float] = Field(default=None, ge=0.0)

class ScheduleRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class ScheduleCreate(BaseModel):
    name: str

class DayConfigRead(BaseModel):
    day_of_week: int
    schedule_id: int

    class Config:
        from_attributes = True

class DayConfigUpdate(BaseModel):
    schedule_id: int

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