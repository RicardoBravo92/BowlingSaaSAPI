# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from app.api.router import api_router
from app.core.logging_config import setup_logging
from app.core.tasks import repeat_cleanup_task

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")