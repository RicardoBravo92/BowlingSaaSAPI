from slowapi import Limiter
from app.core.config import get_settings

settings = get_settings()


def get_client_key(request) -> str:
    """Identifies a client for rate limiting.

    When the API runs behind a reverse proxy / load balancer
    (``BEHIND_PROXY=true``), trust the left-most ``X-Forwarded-For`` value
    (added by the proxy) instead of the container's internal IP.
    """
    if settings.BEHIND_PROXY:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    host = getattr(request.client, "host", None)
    return host or "unknown"


# Redis is used when REDIS_URL is provided, otherwise falls back to memory storage.
limiter = Limiter(
    key_func=get_client_key,
    storage_uri=settings.REDIS_URL if settings.REDIS_URL else "memory://",
)