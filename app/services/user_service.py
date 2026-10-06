from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import user_repository
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
from app.schemas.user import UserCreate, Token
from app.models.enums import UserRole
from app.models.user import User
from app.core.config import get_settings
from app.core.utils import utcnow
from app.core.logging_config import get_logger
from app.services.email_service import email_service

logger = get_logger(__name__)
settings = get_settings()

class UserService:
    async def register_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        """Registers a new user in the system after verifying for duplicates."""
        email = user_in.email.lower()  # normalize so duplicates can't hide in case
        logger.info(f"Attempting to register new user with email: {email}")

        user_exists = await user_repository.get_by_email(db, email=email)
        if user_exists:
            logger.warning(f"Registration failed: User with email {email} already exists.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The email address is already registered."
            )

        hashed_pw = get_password_hash(user_in.password)
        db_user = User(
            email=email,
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=UserRole.USER
        )

        user = await user_repository.create(db, obj_in=db_user)
        logger.info(f"User registered successfully: {user.email} (ID: {user.id})")
        return user

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Token:
        """Validates credentials and generates the JWT token."""
        email = email.lower()
        logger.info(f"Authentication attempt for email: {email}")
        user = await user_repository.get_by_email(db, email=email)
        
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Failed login attempt for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(data={"sub": str(user.id)})
        logger.info(f"User authenticated successfully: {email} (ID: {user.id})")
        return Token(
            access_token=access_token,
            token_type="bearer"
        )

    async def get_user_profile(self, db: AsyncSession, user_id: int) -> User:
        """Retrieves the profile information of the logged-in user."""
        user = await user_repository.get(db, user_id)
        if not user:
            logger.error(f"User profile not found for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def request_password_reset(self, db: AsyncSession, email: str, background_tasks=None):
        """Generates a reset token and sends an email."""
        email = email.lower()
        logger.info(f"Password reset requested for: {email}")
        user = await user_repository.get_by_email(db, email=email)
        
        if not user:
            # We return OK even if user doesn't exist for security (avoid email harvesting)
            logger.info(f"Password reset request ignored: {email} not found.")
            return

        # Create a token valid for 15 minutes (type="reset" so access-token
        # validators reject it)
        reset_token = create_access_token(
            data={"sub": str(user.id)},
            token_type="reset",
            expires_delta=timedelta(minutes=15),
        )
        
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        email_data = {"full_name": user.full_name, "reset_link": reset_link}
        
        if background_tasks:
            background_tasks.add_task(
                email_service.send_password_reset,
                user.email,
                email_data
            )
        else:
            await email_service.send_password_reset(user.email, email_data)
            
        logger.info(f"Password reset email sent to: {email}")

    async def reset_password(self, db: AsyncSession, token: str, new_password: str):
        """Validates the token and updates the password.

        Password changes invalidate every previously issued token because
        ``password_changed_at`` is compared against the ``iat`` claim in
        ``get_current_user``. Combined with the 15-minute lifetime, this makes
        reset tokens effectively single-use.
        """
        payload = decode_token(token)
        if not payload or payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        user_id = payload.get("sub")
        user = await user_repository.get(db, int(user_id))
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.hashed_password = get_password_hash(new_password)
        user.password_changed_at = utcnow()
        await db.commit()
        logger.info(f"Password reset successful for user ID: {user_id}")

user_service = UserService()