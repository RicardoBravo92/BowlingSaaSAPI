from datetime import time
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums import LaneType

if TYPE_CHECKING:
    from app.models.booking import BookingItem

class Lane(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: str = Field(index=True)
    type: LaneType = Field(default=LaneType.NORMAL)
    items: List["BookingItem"] = Relationship(back_populates="lane")

class Schedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str # e.g., "High Season", "Monday to Thursday"
    price_slots: List["PriceSlot"] = Relationship(back_populates="schedule")
    days: List["DayConfig"] = Relationship(back_populates="schedule")

class DayConfig(SQLModel, table=True):
    day_of_week: int = Field(primary_key=True) # 0-6
    schedule_id: int = Field(foreign_key="schedule.id")
    schedule: Schedule = Relationship(back_populates="days")

class PriceSlot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: time
    end_time: time
    price: float
    schedule_id: int = Field(foreign_key="schedule.id")
    schedule: Schedule = Relationship(back_populates="price_slots")
    items: List["BookingItem"] = Relationship(back_populates="price_slot")