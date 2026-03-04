from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize the limiter
# For now, it uses memory-based storage. In production with multiple workers, 
# you'd want to use Redis: Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
limiter = Limiter(key_func=get_remote_address)
