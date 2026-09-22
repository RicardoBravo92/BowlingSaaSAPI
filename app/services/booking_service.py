from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.core.utils import localnow, utcnow
from app.models.booking import Booking, BookingItem
from app.models.enums import BookingStatus
from app.repositories.booking_repository import booking_repo
from app.repositories.infrastructure_repository import infrastructure_repo
from app.schemas.booking import AdminBookingDetail, BookingCreate, BookingDetail, BookingItemDetail
from app.services.email_service import email_service

logger = get_logger(__name__)

class BookingService:
    async def create_reservation(self, db: AsyncSession, user_id: int, data: BookingCreate):
        logger.info(f"User {user_id} attempting to create multi-lane reservation for date {data.booking_date}")
        
        parsed_slots = []
        unique_lane_ids = set()
        
        for key in data.slot_keys:
            try:
                lane_id_str, slot_id_str, start_hour_str = key.split(":")
                lane_id = int(lane_id_str)
                slot_id = int(slot_id_str)
                start_hour = int(start_hour_str)
                
                parsed_slots.append({
                    "lane_id": lane_id,
                    "slot_id": slot_id,
                    "start_hour": start_hour
                })
                unique_lane_ids.add(lane_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid slot key format. Expected lane:slot:hour")

        if not parsed_slots:
            raise HTTPException(status_code=400, detail="No slots selected.")

        # Reject dates/hours that are already in the past (venue local time)
        now = localnow()
        if data.booking_date < now.date():
            logger.warning(f"Booking failed for user {user_id}: date {data.booking_date} is in the past.")
            raise HTTPException(status_code=400, detail="Cannot book a date in the past.")
        is_today = data.booking_date == now.date()

        # Fetch required lanes
        lanes = await infrastructure_repo.get_lanes_by_ids(db, list(unique_lane_ids))
        lanes_by_id = {L.id: L for L in lanes}
        
        if len(lanes_by_id) != len(unique_lane_ids):
            raise HTTPException(status_code=400, detail="One or more invalid lanes selected.")

        # Fetch occupied
        occupied = await booking_repo.get_occupied_slots(db, data.booking_date)
        
        # We need all unique slot_ids from the parsed pairs to fetch their pricing
        unique_slot_ids = list({s["slot_id"] for s in parsed_slots})
        slots = await infrastructure_repo.get_slots_by_ids(db, unique_slot_ids)
        slots_by_id = {s.id: s for s in slots}

        total_price = 0
        items_to_create = []

        for p_slot in parsed_slots:
            lane_id = p_slot["lane_id"]
            slot_id = p_slot["slot_id"]
            start_hour = p_slot["start_hour"]
            
            lane = lanes_by_id[lane_id]

            if slot_id not in slots_by_id:
                raise HTTPException(status_code=400, detail=f"Invalid slot {slot_id}.")
            
            slot = slots_by_id[slot_id]
            
            # Verify hour is within bounds
            if start_hour < slot.start_time.hour or start_hour >= slot.end_time.hour:
                raise HTTPException(status_code=400, detail=f"Invalid hour for slot {slot_id}.")

            # Reject hours that have already passed today
            if is_today and start_hour <= now.hour:
                logger.warning(f"Booking failed for user {user_id}: hour {start_hour} has already passed.")
                raise HTTPException(status_code=400, detail="Cannot book a time slot that has already passed today.")

            # Validate availability
            if (lane_id, slot_id, start_hour) in occupied:
                logger.warning(f"Booking failed for user {user_id}: Slot {slot_id}:{start_hour} on lane {lane_id} is already occupied.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more selected time slots are no longer available."
                )

            # Get the correct price for the lane type
            price = slot.premium_price if lane.type.value == "PREMIUM" else slot.price
            total_price += price
            
            items_to_create.append({
                "lane_id": lane_id,
                "price_slot_id": slot_id, 
                "start_hour": start_hour
            })

        # 4. Create booking header with expiration
        new_booking = Booking(
            user_id=user_id,
            booking_date=data.booking_date,
            total_price=total_price,
            status=BookingStatus.PENDING,
            expires_at=utcnow() + timedelta(minutes=10)
        )
        db.add(new_booking)
        await db.flush() # To obtain the booking ID

        # 5. Create items
        for item_data in items_to_create:
            item = BookingItem(
                booking_id=new_booking.id,
                lane_id=item_data["lane_id"],
                price_slot_id=item_data["price_slot_id"],
                start_hour=item_data["start_hour"]
            )
            db.add(item)

        await db.commit()
        await db.refresh(new_booking)
        logger.info(f"Reservation created successfully for user {user_id}: Booking ID {new_booking.id}")
        return new_booking

    async def confirm_payment(self, db: AsyncSession, booking_id: int, background_tasks=None):
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
            if background_tasks:
                background_tasks.add_task(
                    email_service.send_booking_confirmation, 
                    booking.user.email, 
                    email_data
                )
            else:
                # Fallback if no background tasks provided (e.g. tests or manual calls)
                await email_service.send_booking_confirmation(booking.user.email, email_data)
        except Exception as e:
            logger.error(f"Error sending confirmation email for booking {booking_id}: {e!s}")
            # We don't rollback payment confirmation if email fails

        return booking

    async def cancel_reservation(self, db: AsyncSession, booking_id: int, user_id: int) -> BookingDetail:
        """Cancels a booking owned by the user, as long as it is not already cancelled."""
        logger.info(f"User {user_id} attempting to cancel Booking ID {booking_id}")

        booking = await booking_repo.get_by_id_and_user(db, booking_id, user_id)

        if not booking:
            logger.warning(f"Cancel failed: Booking ID {booking_id} not found for user {user_id}.")
            raise HTTPException(status_code=404, detail="Booking not found")

        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Booking is already cancelled")

        booking.status = BookingStatus.CANCELLED
        await db.commit()
        logger.info(f"Booking ID {booking_id} cancelled by user {user_id}.")
        return self._to_detail(booking)

    def _to_detail(self, booking: Booking) -> BookingDetail:
        return BookingDetail(
            id=booking.id,
            booking_date=booking.booking_date,
            total_price=booking.total_price,
            status=booking.status,
            expires_at=booking.expires_at,
            created_at=booking.created_at,
            items=[
                BookingItemDetail(
                    lane_id=item.lane_id,
                    lane_number=item.lane.number,
                    start_hour=item.start_hour,
                )
                for item in booking.items
            ],
        )

    def _to_admin_detail(self, booking: Booking) -> AdminBookingDetail:
        return AdminBookingDetail(
            id=booking.id,
            user_id=booking.user_id,
            user_full_name=booking.user.full_name,
            user_email=booking.user.email,
            booking_date=booking.booking_date,
            total_price=booking.total_price,
            status=booking.status,
            expires_at=booking.expires_at,
            created_at=booking.created_at,
            items=[
                BookingItemDetail(
                    lane_id=item.lane_id,
                    lane_number=item.lane.number,
                    start_hour=item.start_hour,
                )
                for item in booking.items
            ],
        )

    async def get_all_bookings(
        self,
        db: AsyncSession,
        *,
        status: BookingStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[AdminBookingDetail]:
        """Returns all bookings (staff view) with client info, newest first."""
        bookings = await booking_repo.get_all(
            db, status=status, from_date=from_date, to_date=to_date
        )
        return [self._to_admin_detail(b) for b in bookings]

    async def cancel_booking(self, db: AsyncSession, booking_id: int) -> AdminBookingDetail:
        """Cancels any booking (staff action), as long as it is not already cancelled."""
        logger.info(f"Staff cancelling Booking ID {booking_id}")

        booking = await booking_repo.get_with_details(db, booking_id)

        if not booking:
            logger.warning(f"Cancel failed: Booking ID {booking_id} not found.")
            raise HTTPException(status_code=404, detail="Booking not found")

        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Booking is already cancelled")

        booking.status = BookingStatus.CANCELLED
        detail = self._to_admin_detail(booking)
        await db.commit()
        logger.info(f"Booking ID {booking_id} cancelled by staff.")
        return detail

    async def move_booking(self, db: AsyncSession, booking_id: int, slot_keys: list[str]) -> AdminBookingDetail:
        """Moves a reservation to different lane(s)/time(s) (e.g. damaged lane)."""
        logger.info(f"Staff attempting to move Booking ID {booking_id} to the selected slots")

        booking = await booking_repo.get_with_details(db, booking_id)

        if not booking:
            logger.warning(f"Move failed: Booking ID {booking_id} not found.")
            raise HTTPException(status_code=404, detail="Booking not found")

        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Cannot move a cancelled booking")

        if not slot_keys:
            raise HTTPException(status_code=400, detail="No slots selected.")

        parsed_slots = []
        unique_lane_ids = set()

        for key in slot_keys:
            try:
                lane_id_str, slot_id_str, start_hour_str = key.split(":")
                lane_id = int(lane_id_str)
                slot_id = int(slot_id_str)
                start_hour = int(start_hour_str)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid slot key format. Expected lane:slot:hour")

            parsed_slots.append({"lane_id": lane_id, "slot_id": slot_id, "start_hour": start_hour})
            unique_lane_ids.add(lane_id)

        lanes = await infrastructure_repo.get_lanes_by_ids(db, list(unique_lane_ids))
        lanes_by_id = {L.id: L for L in lanes}

        if len(lanes_by_id) != len(unique_lane_ids):
            raise HTTPException(status_code=400, detail="One or more invalid lanes selected.")

        unique_slot_ids = list({s["slot_id"] for s in parsed_slots})
        slots = await infrastructure_repo.get_slots_by_ids(db, unique_slot_ids)
        slots_by_id = {s.id: s for s in slots}

        # Occupied cells for the day, excluding the booking's own current slots
        occupied = await booking_repo.get_occupied_slots(db, booking.booking_date)
        occupied -= {(i.lane_id, i.price_slot_id, i.start_hour) for i in booking.items}

        total_price = 0
        items_to_create = []

        for p_slot in parsed_slots:
            lane_id = p_slot["lane_id"]
            slot_id = p_slot["slot_id"]
            start_hour = p_slot["start_hour"]

            lane = lanes_by_id[lane_id]

            if slot_id not in slots_by_id:
                raise HTTPException(status_code=400, detail=f"Invalid slot {slot_id}.")

            slot = slots_by_id[slot_id]

            if start_hour < slot.start_time.hour or start_hour >= slot.end_time.hour:
                raise HTTPException(status_code=400, detail=f"Invalid hour for slot {slot_id}.")

            if (lane_id, slot_id, start_hour) in occupied:
                raise HTTPException(status_code=400, detail="One or more selected time slots are no longer available.")

            price = slot.premium_price if lane.type.value == "PREMIUM" else slot.price
            total_price += price

            items_to_create.append({
                "lane_id": lane_id,
                "price_slot_id": slot_id,
                "start_hour": start_hour,
            })

        # Replace the booking's items with the new ones
        for item in booking.items:
            await db.delete(item)
        await db.flush()

        for item_data in items_to_create:
            db.add(
                BookingItem(
                    booking_id=booking.id,
                    lane_id=item_data["lane_id"],
                    price_slot_id=item_data["price_slot_id"],
                    start_hour=item_data["start_hour"],
                )
            )

        booking.total_price = total_price
        await db.commit()
        logger.info(f"Booking ID {booking_id} moved by staff.")

        return AdminBookingDetail(
            id=booking.id,
            user_id=booking.user_id,
            user_full_name=booking.user.full_name,
            user_email=booking.user.email,
            booking_date=booking.booking_date,
            total_price=total_price,
            status=booking.status,
            expires_at=booking.expires_at,
            created_at=booking.created_at,
            items=[
                BookingItemDetail(
                    lane_id=d["lane_id"],
                    lane_number=lanes_by_id[d["lane_id"]].number,
                    start_hour=d["start_hour"],
                )
                for d in items_to_create
            ],
        )

    async def get_user_bookings(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        status: BookingStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[BookingDetail]:
        """Returns all bookings of a user with lane numbers, newest first."""
        bookings = await booking_repo.get_by_user(
            db, user_id, status=status, from_date=from_date, to_date=to_date
        )
        return [self._to_detail(b) for b in bookings]

    async def cleanup_expired_bookings(self, db: AsyncSession):
        """Cancels all bookings that have exceeded their 10-minute payment window."""
        expired_bookings = await booking_repo.get_expired_pending_bookings(db)
        
        if not expired_bookings:
            return 0
            
        count = 0
        for booking in expired_bookings:
            booking.status = BookingStatus.CANCELLED
            count += 1
            logger.info(f"Booking ID {booking.id} has been automatically cancelled due to expiration.")
            
        await db.commit()
        return count

booking_service = BookingService()