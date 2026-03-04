from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.booking import Booking
from app.models.enums import BookingStatus
from datetime import datetime, timedelta

class AnalyticsService:
    async def get_summary_stats(self, db: AsyncSession):
        """Returns overall business metrics."""
        # Total Sales (Paid bookings)
        stmt_sales = select(func.sum(Booking.total_price)).where(Booking.status == BookingStatus.PAID)
        result_sales = await db.execute(stmt_sales)
        total_sales = result_sales.scalar() or 0.0

        # Total Bookings count
        stmt_count = select(func.count(Booking.id)).where(Booking.status == BookingStatus.PAID)
        result_count = await db.execute(stmt_count)
        total_bookings = result_count.scalar() or 0

        # Recent sales (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        stmt_recent = select(func.sum(Booking.total_price)).where(
            and_(
                Booking.status == BookingStatus.PAID,
                Booking.created_at >= seven_days_ago
            )
        )
        result_recent = await db.execute(stmt_recent)
        recent_sales = result_recent.scalar() or 0.0

        return {
            "total_revenue": total_sales,
            "total_paid_bookings": total_bookings,
            "revenue_last_7_days": recent_sales,
            "average_ticket": total_sales / total_bookings if total_bookings > 0 else 0
        }

    async def get_occupancy_report(self, db: AsyncSession, days: int = 30):
        """Calculates occupancy percentage over a period."""
        # This is a simplified version. 
        # Real occupancy would need total possible slots vs occupied slots.
        # For now, let's return bookings per day.
        since_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = (
            select(Booking.booking_date, func.count(Booking.id))
            .where(and_(Booking.status == BookingStatus.PAID, Booking.booking_date >= since_date.date()))
            .group_by(Booking.booking_date)
            .order_by(Booking.booking_date)
        )
        
        result = await db.execute(stmt)
        data = [{"date": str(row[0]), "count": row[1]} for row in result.all()]
        
        return data

analytics_service = AnalyticsService()
