# app/main.py
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import DbDep
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    global_exception_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from app.core.limiter import limiter
from app.core.logging_config import setup_logging
from app.core.tasks import repeat_cleanup_task
from app.schemas.common import HealthRead

# Initialize logging
setup_logging()

settings = get_settings()


def create_app() -> FastAPI:
    """App factory. Creates a configured FastAPI instance."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Start background tasks
        task = asyncio.create_task(repeat_cleanup_task())
        yield
        # Clean up tasks properly
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/health", response_model=HealthRead, tags=["Infrastructure"])
    async def health_check(db: DbDep):
        """
        Check if the API and database are alive.
        Used by Docker/Kubernetes and monitoring tools.
        """
        try:
            await db.execute(text("SELECT 1"))
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {e!s}"

        return {"status": "online", "database": db_status, "version": settings.app_version}

    return app


app = create_app()