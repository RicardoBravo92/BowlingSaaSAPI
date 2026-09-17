
from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserRole


# Information sent by the user during registration
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

# Data returned in APIs (Excluding password)
class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)

# Authentication token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

# Fields that an administrator can update
class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    email: EmailStr | None = None

# Password reset schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str