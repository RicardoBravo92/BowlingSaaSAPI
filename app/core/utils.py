from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current UTC time as a naive datetime, safe for naive TIMESTAMP columns.

    JWT tokens (which require a timezone-aware ``exp``) build their own
    timezone-aware values in :mod:`app.core.security`.
    """
    return datetime.now(UTC).replace(tzinfo=None)