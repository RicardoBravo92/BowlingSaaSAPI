from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.booking import Booking, BookingItem
from app.models.enums import BookingStatus
from app.schemas.booking import BookingCreate
from app.repositories.booking_repository import booking_repo
from app.repositories.infrastructure_repository import infrastructure_repo
from app.core.logging_config import get_logger
from app.services.email_service import email_service

logger = get_logger(__name__)

class BookingService:
    async def create_reservation(self, db: AsyncSession, user_id: int, data: BookingCreate):
        logger.info(f"User {user_id} attempting to create reservation for date {data.booking_date}, lane {data.lane_id}")
        
        # 1. Validate existence and contiguity of selected slots
        slots = await infrastructure_repo.get_slots_by_ids(db, data.selected_slots)
        
        if len(slots) != len(data.selected_slots):
            logger.warning(f"Booking failed for user {user_id}: Invalid slot IDs provided {data.selected_slots}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more selected slots are invalid."
            )

        # Check contiguity (slots are ordered by start_time by the repository)
        for i in range(len(slots) - 1):
            if slots[i].end_time != slots[i+1].start_time:
                logger.warning(f"Booking failed for user {user_id}: Slots are not contiguous {data.selected_slots}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected slots must be contiguous."
                )

        # 2. Validate availability again (to avoid race conditions)
        occupied = await booking_repo.get_occupied_slots(db, data.booking_date)
        
        for slot_id in data.selected_slots:
            if (data.lane_id, slot_id) in occupied:
                logger.warning(f"Booking failed for user {user_id}: Slot {slot_id} on lane {data.lane_id} is already occupied.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The selected time slot is no longer available."
                )

        # 3. Calculate total price (using the objects we already fetched)
        total_price = sum(slot.price for slot in slots)

        # 4. Create booking header with expiration
        new_booking = Booking(
            user_id=user_id,
            booking_date=data.booking_date,
            total_price=total_price,
            status=BookingStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.add(new_booking)
        await db.flush() # To obtain the booking ID

        # 5. Create items (each hour block)
        for slot_id in data.selected_slots:
            item = BookingItem(
                booking_id=new_booking.id,
                lane_id=data.lane_id,
                price_slot_id=slot_id
            )
            db.add(item)

        await db.commit()
        await db.refresh(new_booking)
        logger.info(f"Reservation created successfully for user {user_id}: Booking ID {new_booking.id}")
        return new_booking

    async def confirm_payment(self, db: AsyncSession, booking_id: int):
        """This method is called when the payment gateway gives the OK"""
        logger.info(f"Attempting to confirm payment for Booking ID: {booking_id}")
        
        # Use get_with_details to have everything ready for the email
        booking = await booking_repo.get_with_details(db, booking_id)
        
        if not booking:
            logger.error(f"Payment confirmation failed: Booking ID {booking_id} not found.")
            raise HTTPException(status_code=404, detail="Booking not found")
        
        if booking.status == BookingStatus.PAID:
            logger.info(f"Payment already confirmed for Booking ID: {booking_id}")
            return booking

        booking.status = BookingStatus.PAID
        await db.commit()
        logger.info(f"Payment confirmed successfully for Booking ID: {booking_id}")
        
        # 6. Send Confirmation Email
        try:
            email_data = {
                "full_name": booking.user.full_name,
                "booking_date": booking.booking_date.strftime("%Y-%m-%d"),
                "lane_number": booking.items[0].lane.number,
                "booking_id": booking.id,
                "total_price": booking.total_price
            }
            # Run email sending in the background (fastapi-mail is async)
            await email_service.send_booking_confirmation(booking.user.email, email_data)
        except Exception as e:
            logger.error(f"Error sending confirmation email for booking {booking_id}: {str(e)}")
            # We don't rollback payment confirmation if email fails

        return booking

booking_service = BookingService()