from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.user_service import user_service
from app.schemas.user import UserCreate, UserRead, Token, ForgotPasswordRequest, PasswordResetConfirm

router = APIRouter()

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    return await user_service.register_user(db, user_in)

@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # OAuth2PasswordRequestForm uses 'username' for the email
    return await user_service.authenticate(db, form_data.username, form_data.password)

@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1: User provides email, we send an email with a reset link (token).
    """
    await user_service.request_password_reset(db, data.email)
    return {"message": "If the account exists, a password reset email has been sent."}

@router.post("/reset-password")
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: User provides the token from the email and the new password.
    """
    await user_service.reset_password(db, data.token, data.new_password)
    return {"message": "Password reset successfully."}