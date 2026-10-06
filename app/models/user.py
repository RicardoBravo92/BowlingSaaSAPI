from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.booking import Booking

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    full_name: str
    role: UserRole = Field(default=UserRole.USER)
    # Set whenever the password is changed/reset. Tokens issued before this
    # timestamp (iat claim) are rejected, which invalidates sessions and makes
    # reset tokens effectively single-use.
    password_changed_at: Optional[datetime] = Field(default=None, nullable=True)

    bookings: List["Booking"] = Relationship(back_populates="user")