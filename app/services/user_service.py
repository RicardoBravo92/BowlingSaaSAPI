from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import user_repository
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
from app.schemas.user import UserCreate, Token
from app.models.enums import UserRole
from app.models.user import User
from app.core.logging_config import get_logger
from app.services.email_service import email_service

logger = get_logger(__name__)

class UserService:
    async def register_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        """Registers a new user in the system after verifying for duplicates."""
        logger.info(f"Attempting to register new user with email: {user_in.email}")
        
        user_exists = await user_repository.get_by_email(db, email=user_in.email)
        if user_exists:
            logger.warning(f"Registration failed: User with email {user_in.email} already exists.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The email address is already registered."
            )
        
        hashed_pw = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email,
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=UserRole.USER
        )
        
        user = await user_repository.create(db, obj_in=db_user)
        logger.info(f"User registered successfully: {user.email} (ID: {user.id})")
        return user

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Token:
        """Validates credentials and generates the JWT token."""
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

    async def request_password_reset(self, db: AsyncSession, email: str):
        """Generates a reset token and sends an email."""
        logger.info(f"Password reset requested for: {email}")
        user = await user_repository.get_by_email(db, email=email)
        
        if not user:
            # We return OK even if user doesn't exist for security (avoid email harvesting)
            logger.info(f"Password reset request ignored: {email} not found.")
            return

        # Create a token valid for 15 minutes
        reset_token = create_access_token(
            data={"sub": str(user.id), "type": "reset"}, 
            expires_delta=timedelta(minutes=15)
        )
        
        # In a real app, this link would point to your frontend
        reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
        
        await email_service.send_password_reset(
            user.email, 
            {"full_name": user.full_name, "reset_link": reset_link}
        )
        logger.info(f"Password reset email sent to: {email}")

    async def reset_password(self, db: AsyncSession, token: str, new_password: str):
        """Validates the token and updates the password."""
        payload = decode_token(token)
        if not payload or payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        user_id = payload.get("sub")
        user = await user_repository.get(db, int(user_id))
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.hashed_password = get_password_hash(new_password)
        await db.commit()
        logger.info(f"Password reset successful for user ID: {user_id}")

user_service = UserService()