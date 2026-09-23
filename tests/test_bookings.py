from datetime import date, datetime, time, timedelta

import pytest

from app.core.utils import utcnow
from app.models.enums import LaneType, UserRole
from app.models.infrastructure import DayConfig, Lane, PriceSlot, Schedule
from app.schemas.booking import BookingCreate
from app.schemas.infrastructure import LaneUpdate
from app.services.booking_service import booking_service

# Fixed wall-clock reference used to test past/future hour validation
FIXED_NOW = datetime.combine(date(2026, 1, 15), time(15, 0))


async def _create_pending_booking(db_session, user, lane, slot, start_hour=0, status=None):
    from app.models.booking import Booking, BookingItem
    from app.models.enums import BookingStatus

    booking = Booking(
        user_id=user.id,
        booking_date=utcnow().date(),
        total_price=20.0,
        status=status or BookingStatus.PENDING,
        expires_at=utcnow() + timedelta(minutes=10),
    )
    db_session.add(booking)
    await db_session.flush()

    item = BookingItem(
        booking_id=booking.id,
        lane_id=lane.id,
        price_slot_id=slot.id,
        start_hour=start_hour,
    )
    db_session.add(item)
    await db_session.commit()
    return booking


@pytest.mark.asyncio
async def test_race_condition_concurrent_booking(db_session, client):
    # 1. Setup Infrastructure
    lane = Lane(number="1", type=LaneType.NORMAL)
    db_session.add(lane)
    
    schedule = Schedule(name="Test Schedule")
    db_session.add(schedule)
    await db_session.flush()
    
    # Book a slot on a future date so it is never considered "in the past"
    target_date = utcnow().date() + timedelta(days=1)
    day_config = DayConfig(day_of_week=target_date.weekday(), schedule_id=schedule.id)
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
        booking_date=target_date,
        slot_keys=[f"{lane.id}:{slot.id}:10"]
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
    
    expired_at = utcnow() - timedelta(minutes=1)
    booking = Booking(
        user_id=user.id,
        booking_date=utcnow().date(),
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
    occupied = await booking_repo.get_occupied_slots(db_session, utcnow().date())
    assert (lane.id, slot.id, 0) not in occupied

    # Step 2: Run cleanup task
    cancelled_count = await booking_service.cleanup_expired_bookings(db_session)
    assert cancelled_count >= 1
    
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_pending_booking_succeeds(db_session):
    from app.models.enums import BookingStatus
    from app.models.user import User

    lane = Lane(number="3", type=LaneType.NORMAL)
    schedule = Schedule(name="Cancel Schedule")
    db_session.add_all([lane, schedule])
    await db_session.flush()

    slot = PriceSlot(start_time=time(9, 0), end_time=time(10, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(lane)
    await db_session.refresh(slot)

    user = User(email="cancel@example.com", hashed_password="pw", full_name="Cancel User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    booking = await _create_pending_booking(db_session, user, lane, slot, start_hour=9)

    detail = await booking_service.cancel_reservation(db_session, booking.id, user.id)
    assert detail.status == BookingStatus.CANCELLED

    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_paid_booking_succeeds(db_session):
    from app.models.enums import BookingStatus
    from app.models.user import User

    lane = Lane(number="4", type=LaneType.NORMAL)
    schedule = Schedule(name="Cancel Paid Schedule")
    db_session.add_all([lane, schedule])
    await db_session.flush()

    slot = PriceSlot(start_time=time(9, 0), end_time=time(10, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(lane)
    await db_session.refresh(slot)

    user = User(email="paid@example.com", hashed_password="pw", full_name="Paid User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    booking = await _create_pending_booking(
        db_session, user, lane, slot, start_hour=9, status=BookingStatus.PAID
    )

    detail = await booking_service.cancel_reservation(db_session, booking.id, user.id)
    assert detail.status == BookingStatus.CANCELLED

    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_already_cancelled_booking_is_rejected(db_session):
    from fastapi import HTTPException

    from app.models.enums import BookingStatus
    from app.models.user import User

    lane = Lane(number="10", type=LaneType.NORMAL)
    schedule = Schedule(name="Already Cancelled Schedule")
    db_session.add_all([lane, schedule])
    await db_session.flush()

    slot = PriceSlot(start_time=time(9, 0), end_time=time(10, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(lane)
    await db_session.refresh(slot)

    user = User(email="cancelled@example.com", hashed_password="pw", full_name="Cancelled User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    booking = await _create_pending_booking(
        db_session, user, lane, slot, start_hour=9, status=BookingStatus.CANCELLED
    )

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.cancel_reservation(db_session, booking.id, user.id)

    assert excinfo.value.status_code == 400
    assert "already cancelled" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_cancel_booking_of_other_user_is_not_found(db_session):
    from fastapi import HTTPException

    from app.models.user import User

    lane = Lane(number="5", type=LaneType.NORMAL)
    schedule = Schedule(name="Cancel Ownership Schedule")
    db_session.add_all([lane, schedule])
    await db_session.flush()

    slot = PriceSlot(start_time=time(9, 0), end_time=time(10, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(lane)
    await db_session.refresh(slot)

    owner_user = User(email="owner@example.com", hashed_password="pw", full_name="Owner User")
    other_user = User(email="other@example.com", hashed_password="pw", full_name="Other User")
    db_session.add_all([owner_user, other_user])
    await db_session.commit()
    await db_session.refresh(owner_user)
    await db_session.refresh(other_user)

    booking = await _create_pending_booking(db_session, owner_user, lane, slot, start_hour=9)

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.cancel_reservation(db_session, booking.id, other_user.id)

    assert excinfo.value.status_code == 404


async def _setup_bookable_lane(db_session, lane_number: str):
    lane = Lane(number=lane_number, type=LaneType.NORMAL)
    schedule = Schedule(name=f"Past Slot Schedule {lane_number}")
    db_session.add_all([lane, schedule])
    await db_session.flush()

    slot = PriceSlot(start_time=time(9, 0), end_time=time(20, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(lane)
    await db_session.refresh(slot)

    from app.models.user import User
    user = User(email=f"past{lane_number}@example.com", hashed_password="pw", full_name="Past User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return lane, slot, user


@pytest.mark.asyncio
async def test_cannot_book_past_hour_today(db_session, monkeypatch):
    from fastapi import HTTPException

    import app.services.booking_service as booking_module

    fixed_now = FIXED_NOW
    monkeypatch.setattr(booking_module, "localnow", lambda: fixed_now)

    lane, slot, user = await _setup_bookable_lane(db_session, "6")
    data = BookingCreate(
        booking_date=fixed_now.date(),
        slot_keys=[f"{lane.id}:{slot.id}:10"],
    )

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.create_reservation(db_session, user.id, data)

    assert excinfo.value.status_code == 400
    assert "passed" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_cannot_book_past_date(db_session, monkeypatch):
    from fastapi import HTTPException

    import app.services.booking_service as booking_module

    fixed_now = FIXED_NOW
    monkeypatch.setattr(booking_module, "localnow", lambda: fixed_now)

    lane, slot, user = await _setup_bookable_lane(db_session, "7")
    data = BookingCreate(
        booking_date=fixed_now.date() - timedelta(days=1),
        slot_keys=[f"{lane.id}:{slot.id}:16"],
    )

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.create_reservation(db_session, user.id, data)

    assert excinfo.value.status_code == 400
    assert "past" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_can_book_future_hour_today(db_session, monkeypatch):
    import app.services.booking_service as booking_module

    fixed_now = FIXED_NOW
    monkeypatch.setattr(booking_module, "localnow", lambda: fixed_now)

    lane, slot, user = await _setup_bookable_lane(db_session, "8")
    data = BookingCreate(
        booking_date=fixed_now.date(),
        slot_keys=[f"{lane.id}:{slot.id}:16"],
    )

    booking = await booking_service.create_reservation(db_session, user.id, data)
    assert booking.id is not None


@pytest.mark.asyncio
async def test_grid_marks_past_hours_unavailable(db_session, monkeypatch):
    import app.services.infrastructure_service as infra_module
    from app.services.infrastructure_service import infrastructure_service

    fixed_now = FIXED_NOW
    monkeypatch.setattr(infra_module, "localnow", lambda: fixed_now)

    lane = Lane(number="9", type=LaneType.NORMAL)
    schedule = Schedule(name="Grid Schedule")
    db_session.add_all([lane, schedule])
    await db_session.flush()

    db_session.add(DayConfig(day_of_week=fixed_now.weekday(), schedule_id=schedule.id))
    slot = PriceSlot(start_time=time(9, 0), end_time=time(20, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(lane)
    await db_session.refresh(slot)

    grid = await infrastructure_service.get_grid_availability(db_session, fixed_now.date())
    lane_grid = next(lane_data for lane_data in grid if lane_data["lane_id"] == lane.id)
    availability_by_time = {s["time"]: s["available"] for s in lane_grid["slots"]}

    assert availability_by_time["10:00"] is False
    assert availability_by_time["15:00"] is False
    assert availability_by_time["16:00"] is True


async def _create_booking(db_session, user, lane, slot, booking_date, status):
    from app.models.booking import Booking, BookingItem

    booking = Booking(
        user_id=user.id,
        booking_date=booking_date,
        total_price=20.0,
        status=status,
        expires_at=utcnow() + timedelta(minutes=10),
    )
    db_session.add(booking)
    await db_session.flush()

    db_session.add(BookingItem(booking_id=booking.id, lane_id=lane.id, price_slot_id=slot.id, start_hour=10))
    await db_session.commit()
    return booking


@pytest.mark.asyncio
async def test_get_user_bookings_filter_by_status(db_session):
    from app.models.enums import BookingStatus
    from app.services.booking_service import booking_service

    lane, slot, user = await _setup_bookable_lane(db_session, "F1")
    today = utcnow().date()

    await _create_booking(db_session, user, lane, slot, today, BookingStatus.PENDING)
    await _create_booking(db_session, user, lane, slot, today, BookingStatus.PAID)
    await _create_booking(db_session, user, lane, slot, today, BookingStatus.CANCELLED)

    pending = await booking_service.get_user_bookings(db_session, user.id, status=BookingStatus.PENDING)
    cursed = await booking_service.get_user_bookings(db_session, user.id, status=BookingStatus.CANCELLED)

    assert [b.status for b in pending] == [BookingStatus.PENDING]
    assert [b.status for b in cursed] == [BookingStatus.CANCELLED]


@pytest.mark.asyncio
async def test_get_user_bookings_filter_by_date_range(db_session):
    from app.models.enums import BookingStatus
    from app.services.booking_service import booking_service

    lane, slot, user = await _setup_bookable_lane(db_session, "F2")
    today = utcnow().date()

    await _create_booking(db_session, user, lane, slot, today, BookingStatus.PAID)
    await _create_booking(db_session, user, lane, slot, today - timedelta(days=3), BookingStatus.PAID)
    await _create_booking(db_session, user, lane, slot, today + timedelta(days=5), BookingStatus.PAID)

    result = await booking_service.get_user_bookings(
        db_session, user.id, from_date=today - timedelta(days=1), to_date=today + timedelta(days=1)
    )

    assert len(result) == 1
    assert result[0].booking_date == today


@pytest.mark.asyncio
async def test_my_bookings_endpoint_filters(db_session, client):
    from app.core.security import create_access_token
    from app.models.enums import BookingStatus

    lane, slot, user = await _setup_bookable_lane(db_session, "F3")
    today = utcnow().date()

    await _create_booking(db_session, user, lane, slot, today, BookingStatus.PENDING)
    await _create_booking(db_session, user, lane, slot, today, BookingStatus.PAID)
    await _create_booking(db_session, user, lane, slot, today - timedelta(days=2), BookingStatus.CANCELLED)

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/bookings/my", params={"status": "PENDING"}, headers=headers)
    assert res.status_code == 200
    assert [b["status"] for b in res.json()] == ["PENDING"]

    res = await client.get(
        "/api/v1/bookings/my",
        params={"from_date": (today - timedelta(days=1)).isoformat(), "to_date": today.isoformat()},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 2
    assert all(b["status"] != "CANCELLED" for b in body)

    res = await client.get("/api/v1/bookings/my", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 3


@pytest.mark.asyncio
async def test_get_all_bookings_includes_client_info(db_session):
    from app.models.enums import BookingStatus
    from app.services.booking_service import booking_service

    lane, slot, user = await _setup_bookable_lane(db_session, "F4")
    today = utcnow().date()

    await _create_booking(db_session, user, lane, slot, today, BookingStatus.PAID)
    await _create_booking(db_session, user, lane, slot, today - timedelta(days=1), BookingStatus.CANCELLED)

    all_bookings = await booking_service.get_all_bookings(db_session)
    assert len(all_bookings) == 2
    assert all(b.user_full_name == user.full_name for b in all_bookings)
    assert all(b.user_email == user.email for b in all_bookings)

    only_cancelled = await booking_service.get_all_bookings(db_session, status=BookingStatus.CANCELLED)
    assert len(only_cancelled) == 1
    assert only_cancelled[0].status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_staff_cancel_booking_of_another_user(db_session):
    from app.models.enums import BookingStatus
    from app.services.booking_service import booking_service

    lane, slot, user = await _setup_bookable_lane(db_session, "F5")
    booking = await _create_booking(db_session, user, lane, slot, utcnow().date(), BookingStatus.PENDING)

    detail = await booking_service.cancel_booking(db_session, booking.id)
    assert detail.status == BookingStatus.CANCELLED
    assert detail.user_full_name == user.full_name

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.cancel_booking(db_session, booking.id)
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_admin_bookings_endpoints_require_staff(db_session, client):
    from app.core.security import create_access_token
    from app.models.enums import BookingStatus, UserRole
    from app.models.user import User

    lane, slot, customer = await _setup_bookable_lane(db_session, "F6")
    today = utcnow().date()
    await _create_booking(db_session, customer, lane, slot, today, BookingStatus.PENDING)

    customer_token = create_access_token({"sub": str(customer.id)})

    res = await client.get("/api/v1/admin/bookings", headers={"Authorization": f"Bearer {customer_token}"})
    assert res.status_code == 403

    staff = User(
        email="cashier@example.com",
        hashed_password="pw",
        full_name="Cashier",
        role=UserRole.CASHIER,
    )
    db_session.add(staff)
    await db_session.commit()

    staff_token = create_access_token({"sub": str(staff.id)})
    headers = {"Authorization": f"Bearer {staff_token}"}

    res = await client.get("/api/v1/admin/bookings", params={"status": "PENDING"}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["user_full_name"] == customer.full_name
    assert body[0]["user_email"] == customer.email

    booking_id = body[0]["id"]
    res = await client.delete(f"/api/v1/admin/bookings/{booking_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"

    res = await client.get("/api/v1/admin/bookings", headers=headers)
    assert res.status_code == 200
    assert res.json()[0]["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_move_booking_to_another_lane(db_session):
    from app.models.enums import BookingStatus
    from app.services.booking_service import booking_service

    lane_a, slot_a, user = await _setup_bookable_lane(db_session, "F8")

    lane_b = Lane(number="F9", type=LaneType.NORMAL)
    schedule_b = Schedule(name="Move Schedule")
    db_session.add_all([lane_b, schedule_b])
    await db_session.flush()
    slot_b = PriceSlot(start_time=time(9, 0), end_time=time(20, 0), price=30.0, schedule_id=schedule_b.id)
    db_session.add(slot_b)
    await db_session.commit()
    await db_session.refresh(lane_b)
    await db_session.refresh(slot_b)

    booking = await _create_booking(db_session, user, lane_a, slot_a, utcnow().date(), BookingStatus.PAID)

    moved = await booking_service.move_booking(db_session, booking.id, [f"{lane_b.id}:{slot_b.id}:14"])

    assert moved.status == BookingStatus.PAID
    assert moved.items[0].lane_id == lane_b.id
    assert moved.items[0].start_hour == 14
    assert moved.total_price == 30.0


@pytest.mark.asyncio
async def test_move_booking_to_occupied_slot_fails(db_session):
    from app.models.enums import BookingStatus, UserRole
    from fastapi import HTTPException
    from app.models.user import User
    from app.services.booking_service import booking_service

    lane_a, slot_a, user = await _setup_bookable_lane(db_session, "FA")
    lane_b = Lane(number="FB", type=LaneType.NORMAL)
    schedule_b = Schedule(name="Move Occupied")
    db_session.add_all([lane_b, schedule_b])
    await db_session.flush()
    slot_b = PriceSlot(start_time=time(9, 0), end_time=time(20, 0), price=25.0, schedule_id=schedule_b.id)
    db_session.add(slot_b)
    await db_session.commit()
    await db_session.refresh(lane_b)
    await db_session.refresh(slot_b)

    booking = await _create_booking(db_session, user, lane_a, slot_a, utcnow().date(), BookingStatus.PAID)

    # Another user takes the target cell first (on a future date so no past-hour rules apply)
    target_date = utcnow().date() + timedelta(days=1)
    other = User(email="other@example.com", hashed_password="pw", full_name="Other", role=UserRole.USER)
    db_session.add(other)
    await db_session.commit()
    await booking_service.create_reservation(
        db_session, other.id,
        BookingCreate(booking_date=target_date, slot_keys=[f"{lane_b.id}:{slot_b.id}:14"]),
    )

    # Move the first booking to that same (now occupied) cell
    occupied_booking = await _create_booking(
        db_session, user, lane_a, slot_a, target_date, BookingStatus.PAID
    )
    with pytest.raises(HTTPException) as excinfo:
        await booking_service.move_booking(
            db_session, occupied_booking.id, [f"{lane_b.id}:{slot_b.id}:14"]
        )
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_admin_move_booking_endpoint(db_session, client):
    from app.core.security import create_access_token
    from app.models.enums import BookingStatus, UserRole
    from app.models.user import User

    lane_a, slot_a, customer = await _setup_bookable_lane(db_session, "FD")

    lane_b = Lane(number="FE", type=LaneType.NORMAL)
    schedule_b = Schedule(name="Move Endpoint")
    db_session.add_all([lane_b, schedule_b])
    await db_session.flush()
    slot_b = PriceSlot(start_time=time(9, 0), end_time=time(20, 0), price=35.0, schedule_id=schedule_b.id)
    db_session.add(slot_b)
    await db_session.commit()

    await _create_booking(db_session, customer, lane_a, slot_a, utcnow().date(), BookingStatus.PENDING)

    staff = User(email="move-manager@example.com", hashed_password="pw", full_name="Move Manager", role=UserRole.MANAGER)
    db_session.add(staff)
    await db_session.commit()

    token = create_access_token({"sub": str(staff.id)})
    headers = {"Authorization": f"Bearer {token}"}

    list_res = await client.get("/api/v1/admin/bookings", headers=headers)
    booking_id = list_res.json()[0]["id"]

    res = await client.post(
        f"/api/v1/admin/bookings/{booking_id}/move",
        json={"slot_keys": [f"{lane_b.id}:{slot_b.id}:16"]},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["items"][0]["lane_id"] == lane_b.id
    assert body["items"][0]["start_hour"] == 16
    assert body["total_price"] == 35.0


@pytest.mark.asyncio
async def test_grid_excludes_inactive_lane(db_session):
    from app.services.infrastructure_service import infrastructure_service

    lane_active = Lane(number="G1", type=LaneType.NORMAL)
    lane_inactive = Lane(number="G2", type=LaneType.NORMAL, is_active=False)
    schedule = Schedule(name="Grid Inactive")
    db_session.add_all([lane_active, lane_inactive, schedule])
    await db_session.flush()

    target_date = utcnow().date() + timedelta(days=1)
    db_session.add(DayConfig(day_of_week=target_date.weekday(), schedule_id=schedule.id))
    slot = PriceSlot(start_time=time(9, 0), end_time=time(11, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()

    grid = await infrastructure_service.get_grid_availability(db_session, target_date)
    lane_ids = [lane_data["lane_id"] for lane_data in grid]

    assert lane_active.id in lane_ids
    assert lane_inactive.id not in lane_ids


@pytest.mark.asyncio
async def test_cannot_book_inactive_lane(db_session):
    from fastapi import HTTPException

    lane = Lane(number="G3", type=LaneType.NORMAL, is_active=False)
    schedule = Schedule(name="Inactive Book")
    db_session.add_all([lane, schedule])
    await db_session.flush()
    slot = PriceSlot(start_time=time(9, 0), end_time=time(11, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()

    from app.models.user import User
    user = User(email="inactive@example.com", hashed_password="pw", full_name="Inactive User")
    db_session.add(user)
    await db_session.commit()

    data = BookingCreate(
        booking_date=utcnow().date() + timedelta(days=1),
        slot_keys=[f"{lane.id}:{slot.id}:10"],
    )

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.create_reservation(db_session, user.id, data)

    assert excinfo.value.status_code == 400
    assert "maintenance" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_cannot_move_booking_to_inactive_lane(db_session):
    from fastapi import HTTPException
    from app.models.enums import BookingStatus, UserRole
    from app.services.booking_service import booking_service

    lane_a, slot_a, customer = await _setup_bookable_lane(db_session, "G4")

    lane_b = Lane(number="G5", type=LaneType.NORMAL, is_active=False)
    schedule_b = Schedule(name="Inactive Move")
    db_session.add_all([lane_b, schedule_b])
    await db_session.flush()
    slot_b = PriceSlot(start_time=time(9, 0), end_time=time(20, 0), price=25.0, schedule_id=schedule_b.id)
    db_session.add(slot_b)
    await db_session.commit()

    booking = await _create_booking(db_session, customer, lane_a, slot_a, utcnow().date(), BookingStatus.PAID)

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.move_booking(db_session, booking.id, [f"{lane_b.id}:{slot_b.id}:14"])

    assert excinfo.value.status_code == 400
    assert "maintenance" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_owner_toggles_lane_maintenance_endpoint(db_session, client):
    from app.core.security import create_access_token
    from app.models.user import User
    from app.models.enums import UserRole

    lane = Lane(number="G6", type=LaneType.NORMAL)
    db_session.add(lane)
    await db_session.commit()

    owner = User(email="owner-infra@example.com", hashed_password="pw", full_name="Owner Infra", role=UserRole.OWNER)
    db_session.add(owner)
    await db_session.commit()

    token = create_access_token({"sub": str(owner.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.patch(
        f"/api/v1/infrastructure/lanes/{lane.id}",
        json={"is_active": False},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    res = await client.get(f"/api/v1/infrastructure/lanes", headers=headers)
    lane_data = next(l for l in res.json() if l["id"] == lane.id)
    assert lane_data["is_active"] is False
    assert lane_data["number"] == "G6"


@pytest.mark.asyncio
async def test_toggling_lane_creates_and_closes_maintenance_record(db_session):
    from app.repositories.infrastructure_repository import infrastructure_repo
    from app.services.infrastructure_service import infrastructure_service

    lane = Lane(number="H1", type=LaneType.NORMAL)
    db_session.add(lane)
    await db_session.commit()
    await db_session.refresh(lane)

    # Disable lane -> should open a record
    await infrastructure_service.update_lane(db_session, lane.id, LaneUpdate(is_active=False), changed_by=1)
    open_record = await infrastructure_repo.get_open_maintenance(db_session, lane.id)
    assert open_record is not None
    assert open_record.ended_at is None

    # Re-enable lane -> should close the open record
    await infrastructure_service.update_lane(db_session, lane.id, LaneUpdate(is_active=True), changed_by=1)
    open_record = await infrastructure_repo.get_open_maintenance(db_session, lane.id)
    assert open_record is None

    records = await infrastructure_repo.get_all_maintenance(db_session, lane_id=lane.id)
    assert len(records) == 1
    assert records[0].ended_at is not None
    assert records[0].changed_by == 1


@pytest.mark.asyncio
async def test_maintenance_record_reason_is_saved(db_session):
    from app.repositories.infrastructure_repository import infrastructure_repo
    from app.services.infrastructure_service import infrastructure_service

    lane = Lane(number="H2", type=LaneType.NORMAL)
    db_session.add(lane)
    await db_session.commit()
    await db_session.refresh(lane)

    await infrastructure_service.update_lane(
        db_session, lane.id,
        LaneUpdate(is_active=False, maintenance_reason="Limpieza y encerado"),
        changed_by=1,
    )
    open_record = await infrastructure_repo.get_open_maintenance(db_session, lane.id)
    assert open_record.reason == "Limpieza y encerado"


@pytest.mark.asyncio
async def test_maintenance_history_endpoint(db_session, client):
    from app.core.security import create_access_token
    from app.models.user import User
    from app.models.enums import UserRole

    lane = Lane(number="H3", type=LaneType.NORMAL)
    db_session.add(lane)
    await db_session.commit()

    staff = User(email="mt-staff@example.com", hashed_password="pw", full_name="MT Staff", role=UserRole.MAINTENANCE)
    db_session.add(staff)
    await db_session.commit()

    from app.services.infrastructure_service import infrastructure_service
    await infrastructure_service.update_lane(db_session, lane.id, LaneUpdate(is_active=False), changed_by=staff.id)
    await infrastructure_service.update_lane(db_session, lane.id, LaneUpdate(is_active=True), changed_by=staff.id)

    token = create_access_token({"sub": str(staff.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/infrastructure/lanes/maintenance", headers=headers)
    assert res.status_code == 200
    records = res.json()
    assert len(records) == 1
    assert records[0]["lane_id"] == lane.id
    assert records[0]["lane_number"] == "H3"
    assert records[0]["ended_at"] is not None

    # Filter by lane_id
    res = await client.get(f"/api/v1/infrastructure/lanes/maintenance?lane_id={lane.id}", headers=headers)
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_assign_lane_creates_assigned_booking_and_blocks_slot(db_session):
    from app.models.enums import BookingStatus
    from app.repositories.booking_repository import booking_repo
    from app.schemas.booking import BookingAssign
    from app.services.booking_service import booking_service

    lane, slot, user = await _setup_bookable_lane(db_session, "AS1")
    target_date = utcnow().date() + timedelta(days=1)

    detail = await booking_service.assign_lane(
        db_session,
        BookingAssign(user_id=user.id, booking_date=target_date, slot_keys=[f"{lane.id}:{slot.id}:10"]),
    )

    assert detail.status == BookingStatus.ASSIGNED
    assert detail.total_price == 0
    assert detail.user_full_name == user.full_name
    assert detail.items[0].lane_id == lane.id

    # The assigned slot must be considered occupied
    occupied = await booking_repo.get_occupied_slots(db_session, target_date)
    assert (lane.id, slot.id, 10) in occupied

    # A second assignment on the same slot must fail
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.assign_lane(
            db_session,
            BookingAssign(user_id=user.id, booking_date=target_date, slot_keys=[f"{lane.id}:{slot.id}:10"]),
        )
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_assign_lane_rejects_unknown_user(db_session):
    from fastapi import HTTPException
    from app.schemas.booking import BookingAssign
    from app.services.booking_service import booking_service

    lane, slot, _ = await _setup_bookable_lane(db_session, "AS2")

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.assign_lane(
            db_session,
            BookingAssign(user_id=999999, booking_date=utcnow().date() + timedelta(days=1), slot_keys=[f"{lane.id}:{slot.id}:10"]),
        )
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_assign_lane_rejects_inactive_lane(db_session):
    from fastapi import HTTPException
    from app.schemas.booking import BookingAssign
    from app.services.booking_service import booking_service

    lane = Lane(number="AS3", type=LaneType.NORMAL, is_active=False)
    schedule = Schedule(name="Assign Inactive")
    db_session.add_all([lane, schedule])
    await db_session.flush()
    slot = PriceSlot(start_time=time(9, 0), end_time=time(11, 0), price=20.0, schedule_id=schedule.id)
    db_session.add(slot)
    await db_session.commit()

    from app.models.user import User
    user = User(email="assign-inactive@example.com", hashed_password="pw", full_name="Assign Inactive")
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(HTTPException) as excinfo:
        await booking_service.assign_lane(
            db_session,
            BookingAssign(user_id=user.id, booking_date=utcnow().date() + timedelta(days=1), slot_keys=[f"{lane.id}:{slot.id}:10"]),
        )
    assert excinfo.value.status_code == 400
    assert "maintenance" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_assign_does_not_count_as_revenue(db_session):
    from app.models.enums import BookingStatus
    from app.schemas.booking import BookingAssign
    from app.services.analytics_service import analytics_service
    from app.services.booking_service import booking_service

    lane, slot, user = await _setup_bookable_lane(db_session, "AS4")

    # A normal paid booking adds revenue
    today = utcnow().date()
    await _create_booking(db_session, user, lane, slot, today, BookingStatus.PAID)

    # Assign a gifted booking (total 0) for another date
    await booking_service.assign_lane(
        db_session,
        BookingAssign(user_id=user.id, booking_date=today + timedelta(days=1), slot_keys=[f"{lane.id}:{slot.id}:10"]),
    )

    stats = await analytics_service.get_summary_stats(db_session)
    assert stats["total_paid_bookings"] == 1
    assert stats["total_revenue"] == 20.0


@pytest.mark.asyncio
async def test_admin_assign_booking_endpoint(db_session, client):
    from app.core.security import create_access_token
    from app.models.user import User
    from app.models.enums import UserRole

    lane, slot, customer = await _setup_bookable_lane(db_session, "AS5")
    target_date = utcnow().date() + timedelta(days=1)

    staff = User(email="assign-cashier@example.com", hashed_password="pw", full_name="Assign Cashier", role=UserRole.CASHIER)
    db_session.add(staff)
    await db_session.commit()

    token = create_access_token({"sub": str(staff.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/admin/bookings/assign",
        json={
            "user_id": customer.id,
            "booking_date": target_date.isoformat(),
            "slot_keys": [f"{lane.id}:{slot.id}:12"],
        },
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ASSIGNED"
    assert body["total_price"] == 0
    assert body["user_full_name"] == customer.full_name


@pytest.mark.asyncio
async def test_admin_assign_endpoint_requires_staff(db_session, client):
    from app.core.security import create_access_token

    lane, slot, customer = await _setup_bookable_lane(db_session, "AS6")
    target_date = utcnow().date() + timedelta(days=1)

    token = create_access_token({"sub": str(customer.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/admin/bookings/assign",
        json={
            "user_id": customer.id,
            "booking_date": target_date.isoformat(),
            "slot_keys": [f"{lane.id}:{slot.id}:12"],
        },
        headers=headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_search_users_endpoint(db_session, client):
    from app.core.security import create_access_token
    from app.models.user import User
    from app.models.enums import UserRole

    db_session.add_all([
        User(email="alex@gmail.com", hashed_password="pw", full_name="Alex Rivas", role=UserRole.USER),
        User(email="maria@gmail.com", hashed_password="pw", full_name="Maria Perez", role=UserRole.USER),
    ])
    await db_session.commit()

    staff = User(email="search-cashier@example.com", hashed_password="pw", full_name="Search Cashier", role=UserRole.CASHIER)
    db_session.add(staff)
    await db_session.commit()

    token = create_access_token({"sub": str(staff.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/admin/users/search", params={"q": "alex"}, headers=headers)
    assert res.status_code == 200
    names = [u["full_name"] for u in res.json()]
    assert "Alex Rivas" in names

    res = await client.get("/api/v1/admin/users/search", params={"q": "gmail.com"}, headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 2

    res = await client.get("/api/v1/admin/users/search", params={"q": "nobody"}, headers=headers)
    assert len(res.json()) == 0
