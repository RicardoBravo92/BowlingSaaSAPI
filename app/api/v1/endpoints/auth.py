from fastapi import APIRouter, Depends, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.user_service import user_service
from app.schemas.user import UserCreate, UserRead, Token, ForgotPasswordRequest, PasswordResetConfirm
from app.core.limiter import limiter

router = APIRouter()

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    return await user_service.register_user(db, user_in)

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # OAuth2PasswordRequestForm uses 'username' for the email
    return await user_service.authenticate(db, form_data.username, form_data.password)

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Step 1: User provides email, we send an email with a reset link (token).
    """
    await user_service.request_password_reset(db, data.email, background_tasks=background_tasks)
    return {"message": "If the account exists, a password reset email has been sent."}

@router.get("/me", response_model=UserRead)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Returns the profile of the currently authenticated user."""
    return current_user

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