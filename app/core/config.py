from pydantic_settings import BaseSettings
from functools import lru_cache
import sys
import logging
from typing import Optional

class Settings(BaseSettings):
    """Application settings."""
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_V1_STR: str = "/api/v1"

    # Email Settings
    MAIL_USERNAME: str = "your_email@example.com"
    MAIL_PASSWORD: str = "your_password"
    MAIL_FROM: str = "no-reply@bowlingsaas.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        logger = logging.getLogger("config")
        logger.error("Required environment variables are missing or invalid in your .env file")
        logger.error(f"Error details: {str(e)}")
        logger.info("\nExample of a minimal .env file:")
        logger.info("DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname")
        logger.info("SECRET_KEY=supersecretkey")
        sys.exit(1)