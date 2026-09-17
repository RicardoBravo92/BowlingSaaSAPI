from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class HealthRead(BaseModel):
    status: str
    database: str
    version: str