from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from app.core.config import get_settings

settings = get_settings()

# For asyncpg, especially with Neon, we might need to handle the sslmode parameter
# because asyncpg uses 'ssl' instead of 'sslmode'
engine_kwargs = {
    "echo": True,
    "future": True
}

if "postgresql+asyncpg" in settings.DATABASE_URL:
    # If using Neon/Postgres with sslmode, we filter it and pass via connect_args
    # This prevents the "Unexpected keyword argument 'sslmode'" error
    if "sslmode" in settings.DATABASE_URL:
        engine_kwargs["connect_args"] = {"ssl": True}
        # Clean the URL from query parameters that asyncpg doesn't like
        clean_url = settings.DATABASE_URL.split("?")[0]
        db_url = clean_url
    else:
        db_url = settings.DATABASE_URL
else:
    db_url = settings.DATABASE_URL

engine = create_async_engine(db_url, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """Dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()