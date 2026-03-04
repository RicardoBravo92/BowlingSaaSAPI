import pytest
from datetime import date, time, datetime, timedelta
from app.models.infrastructure import Lane, Schedule, DayConfig, PriceSlot
from app.models.enums import UserRole, LaneType
from app.services.booking_service import booking_service
from app.schemas.booking import BookingCreate

@pytest.mark.asyncio
async def test_race_condition_concurrent_booking(db_session, client):
    # 1. Setup Infrastructure
    lane = Lane(number="1", type=LaneType.NORMAL)
    db_session.add(lane)
    
    schedule = Schedule(name="Test Schedule")
    db_session.add(schedule)
    await db_session.flush()
    
    # Create a slot for today
    today = date.today()
    day_config = DayConfig(day_of_week=today.weekday(), schedule_id=schedule.id)
    db_session.add(day_config)
    
    slot = PriceSlot(
        start_time=time(10, 0),
        end_time=time(11, 0),
        price=20.0,
        schedule_id=schedule.id
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(lane)
    await db_session.refresh(slot)

    # 2. Setup user
    from app.core.security import get_password_hash
    from app.models.user import User
    user = User(email="customer@example.com", hashed_password=get_password_hash("password"), full_name="Customer", role=UserRole.USER)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 3. Simulate two concurrent requests to the same slot
    # Note: In a real environment we'd use multiple processes/threads. 
    # Here we test if the service properly detects occupation.
    
    booking_data = BookingCreate(
        lane_id=lane.id,
        booking_date=today,
        selected_slots=[slot.id]
    )

    # First booking succeeds
    res1 = await booking_service.create_reservation(db_session, user.id, booking_data)
    assert res1.id is not None

    # Second booking should fail because the slot is now occupied (Pending and not expired)
    with pytest.raises(Exception) as excinfo:
        await booking_service.create_reservation(db_session, user.id, booking_data)
    
    assert "no longer available" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_booking_expiration_and_slot_release(db_session):
    # Setup similar to above but with an expired booking
    lane = Lane(number="2", type=LaneType.NORMAL)
    db_session.add(lane)
    schedule = Schedule(name="Expired Task Schedule")
    db_session.add(schedule)
    await db_session.flush()
    
    slot = PriceSlot(start_time=time(14, 0), end_time=time(15, 0), price=25.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)

    from app.models.user import User
    user = User(email="test2@example.com", hashed_password="pw", full_name="Test User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create an EXPIRED pending booking
    from app.models.booking import Booking, BookingItem
    from app.models.enums import BookingStatus
    
    expired_at = datetime.utcnow() - timedelta(minutes=1)
    booking = Booking(
        user_id=user.id,
        booking_date=date.today(),
        total_price=25.0,
        status=BookingStatus.PENDING,
        expires_at=expired_at
    )
    db_session.add(booking)
    await db_session.flush()
    
    item = BookingItem(booking_id=booking.id, lane_id=lane.id, price_slot_id=slot.id)
    db_session.add(item)
    await db_session.commit()

    # Step 1: Verify slot is considered AVAILABLE because booking is expired
    from app.repositories.booking_repository import booking_repo
    occupied = await booking_repo.get_occupied_slots(db_session, date.today())
    assert (lane.id, slot.id) not in occupied

    # Step 2: Run cleanup task
    cancelled_count = await booking_service.cleanup_expired_bookings(db_session)
    assert cancelled_count >= 1
    
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED
