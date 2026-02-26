from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import ALGORITHM
from app.core.config import get_settings
from app.repositories.user_repository import user_repository
from app.models.enums import UserRole
from app.models.user import User

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Retrieves the current authenticated user via JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await user_repository.get(db, int(user_id))
    if user is None:
        raise credentials_exception

    return user


def check_role(user: User, allowed_roles: list[UserRole]):
    """Verifies if the user has one of the allowed roles."""
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have sufficient permissions to perform this action"
        )

async def get_current_active_owner(user: User = Depends(get_current_user)) -> User:
    """Filters only for the Owner (Super Admin)."""
    check_role(user, [UserRole.OWNER])
    return user

async def get_current_active_manager(user: User = Depends(get_current_user)) -> User:
    """Filters for Managers and Owners."""
    check_role(user, [UserRole.MANAGER, UserRole.OWNER])
    return user

async def get_current_active_cashier(user: User = Depends(get_current_user)) -> User:
    """Filters for Cashiers, Managers, and Owners."""
    check_role(user, [UserRole.CASHIER, UserRole.MANAGER, UserRole.OWNER])
    return user

async def get_current_active_maintenance(user: User = Depends(get_current_user)) -> User:
    """Filters for Maintenance staff, Managers, and Owners."""
    check_role(user, [UserRole.MAINTENANCE, UserRole.MANAGER, UserRole.OWNER])
    return user