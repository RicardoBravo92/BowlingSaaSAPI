import logging
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Bowling SaaS API"
    app_version: str = "1.0.0"

    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_V1_STR: str = "/api/v1"

    # Business timezone (IANA name) used to validate wall-clock booking hours
    TIMEZONE: str = "America/Caracas"

    # Email Settings
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str = "no-reply@bowlingsaas.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    REDIS_URL: str | None = None
    USE_CREDENTIALS: bool = True

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://your-frontend-domain.com",
    ]


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        logger = logging.getLogger("config")
        logger.error(
            "Required environment variables are missing or invalid in your .env file"
        )
        logger.error(f"Error details: {e!s}")
        logger.info("\nExample of a minimal .env file:")
        logger.info("DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname")
        logger.info("SECRET_KEY=supersecretkey")
        sys.exit(1)
