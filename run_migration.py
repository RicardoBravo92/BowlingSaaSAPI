import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os

raw_url = os.environ.get("DATABASE_URL").strip("'\"")
DATABASE_URL = raw_url.split("?")[0]

async def main():
    print(f"Connecting to {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        from sqlalchemy import text
        try:
            await conn.execute(text("ALTER TABLE bookingitem ADD COLUMN start_hour INTEGER NOT NULL DEFAULT 0;"))
            print("Successfully added start_hour column.")
        except Exception as e:
            print(f"Error adding column (it might already exist): {e}")

if __name__ == "__main__":
    asyncio.run(main())
