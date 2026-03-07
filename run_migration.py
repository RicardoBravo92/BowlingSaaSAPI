import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

async def main():
    print(f"Connecting to {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        from sqlalchemy import text
        # Check if the column exists first to be safe, or just try to add
        try:
            await conn.execute(text("ALTER TABLE priceslot ADD COLUMN premium_price FLOAT NOT NULL DEFAULT 0.0;"))
            print("Successfully added premium_price column.")
        except Exception as e:
            print(f"Error adding column (it might already exist): {e}")

if __name__ == "__main__":
    asyncio.run(main())
