import asyncio
from app.services.booking_service import booking_service
from app.core.database import AsyncSessionLocal
from app.core.logging_config import get_logger

logger = get_logger(__name__)

async def repeat_cleanup_task():
    """Runs a periodic cleanup of expired bookings every 5 minutes."""
    logger.info("Starting background task for booking cleanup.")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                count = await booking_service.cleanup_expired_bookings(db)
                if count > 0:
                    logger.info(f"Periodic Cleanup: {count} bookings cancelled automatically.")
        except Exception as e:
            logger.error(f"Error in background task 'repeat_cleanup_task': {str(e)}")
            
        # Wait for 5 minutes (300 seconds)
        await asyncio.sleep(300)
