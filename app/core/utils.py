from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    """Current UTC time as a naive datetime, safe for naive TIMESTAMP columns.

    JWT tokens (which require a timezone-aware ``exp``) build their own
    timezone-aware values in :mod:`app.core.security`.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def localnow() -> datetime:
    """Current time in the configured business timezone as a naive datetime.

    Used to compare against wall-clock booking hours (``booking_date`` +
    ``start_hour``), which are expressed in the venue's local time.
    """
    from app.core.config import get_settings

    tz = ZoneInfo(get_settings().TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None)