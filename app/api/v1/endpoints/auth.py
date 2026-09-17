from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import CurrentUserDep, DbDep
from app.core.limiter import limiter
from app.schemas.common import MessageResponse
from app.schemas.user import (
    ForgotPasswordRequest,
    PasswordResetConfirm,
    Token,
    UserCreate,
    UserRead,
)
from app.services.user_service import user_service

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate, db: DbDep):
    return await user_service.register_user(db, user_in)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    db: DbDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    # OAuth2PasswordRequestForm uses 'username' for the email
    return await user_service.authenticate(db, form_data.username, form_data.password)


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: DbDep,
    background_tasks: BackgroundTasks,
):
    """
    Step 1: User provides email, we send an email with a reset link (token).
    """
    await user_service.request_password_reset(db, data.email, background_tasks=background_tasks)
    return MessageResponse(message="If the account exists, a password reset email has been sent.")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUserDep):
    """Returns the profile of the currently authenticated user."""
    return current_user


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: PasswordResetConfirm, db: DbDep):
    """
    Step 2: User provides the token from the email and the new password.
    """
    await user_service.reset_password(db, data.token, data.new_password)
    return MessageResponse(message="Password reset successfully.")