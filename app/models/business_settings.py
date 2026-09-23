from typing import Optional
from sqlmodel import SQLModel, Field


class BusinessSettings(SQLModel, table=True):
    """Single-row table holding the business identity shown to customers
    (name, address, phone). There is only ever one row (id = 1)."""
    id: Optional[int] = Field(default=1, primary_key=True)
    name: str = Field(default="Bowling SaaS")
    address: str = Field(default="")
    phone: str = Field(default="")