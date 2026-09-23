from pydantic import BaseModel, ConfigDict


class BusinessSettingsRead(BaseModel):
    id: int
    name: str
    address: str
    phone: str

    model_config = ConfigDict(from_attributes=True)


class BusinessSettingsUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None