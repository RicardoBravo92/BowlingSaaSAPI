
from pydantic import BaseModel


class SummaryStats(BaseModel):
    total_revenue: float
    total_paid_bookings: int
    revenue_last_7_days: float
    average_ticket: float


class OccupancyPoint(BaseModel):
    date: str
    count: int


class StatsRead(BaseModel):
    summary: SummaryStats
    daily_history: list[OccupancyPoint]
    period: str