from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from app.core.config import get_settings

settings = get_settings()


engine_kwargs = {
    "echo": True,
    "future": True
}

if "postgresql+asyncpg" in settings.DATABASE_URL:
    if "sslmode" in settings.DATABASE_URL:
        engine_kwargs["connect_args"] = {"ssl": True}
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