# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from app.api.router import api_router
from app.core.logging_config import setup_logging
from app.core.tasks import repeat_cleanup_task
from app.core.limiter import limiter
from app.core.exceptions import (
    global_exception_handler, 
    validation_exception_handler, 
    sqlalchemy_exception_handler
)
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

# Initialize logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    task = asyncio.create_task(repeat_cleanup_task())
    yield
    # Clean up tasks if needed
    task.cancel()

app = FastAPI(title="Bowling SaaS API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Infrastructure"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check if the API and database are alive.
    Used by Docker/Kubernetes and monitoring tools.
    """
    try:
        from sqlalchemy import text
        # Simple query to check DB connection
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "online",
        "database": db_status,
        "version": "1.0.0"
    }

app.include_router(api_router, prefix="/api/v1")