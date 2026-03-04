from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import get_settings

settings = get_settings()

# Initialize the limiter
# It uses Redis if REDIS_URL is provided, otherwise falls back to memory storage.
limiter = Limiter(
    key_func=get_remote_address, 
    storage_uri=settings.REDIS_URL if settings.REDIS_URL else "memory://"
)
