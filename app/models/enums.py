from enum import Enum

class UserRole(str, Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    CASHIER = "CASHIER"
    MAINTENANCE = "MAINTENANCE"
    USER = "USER"

class LaneType(str, Enum):
    NORMAL = "NORMAL"
    PREMIUM = "PREMIUM"

class BookingStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"