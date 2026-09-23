from datetime import datetime, time
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.core.utils import utcnow
from app.models.enums import LaneType

if TYPE_CHECKING:
    from app.models.booking import BookingItem

class Lane(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: str = Field(index=True)
    type: LaneType = Field(default=LaneType.NORMAL)
    is_active: bool = Field(default=True)
    items: List["BookingItem"] = Relationship(back_populates="lane")

class MaintenanceRecord(SQLModel, table=True):
    """One maintenance episode for a lane: created when the lane is disabled,
    closed when it is reactivated (ended_at null means still under maintenance)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    lane_id: int = Field(foreign_key="lane.id", index=True)
    reason: Optional[str] = None
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: Optional[datetime] = None
    changed_by: Optional[int] = Field(default=None, foreign_key="user.id")

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
    premium_price: float = Field(default=0.0)
    schedule_id: int = Field(foreign_key="schedule.id")
    schedule: Schedule = Relationship(back_populates="price_slots")
    items: List["BookingItem"] = Relationship(back_populates="price_slot")