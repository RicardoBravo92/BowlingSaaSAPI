import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check_enum():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'userrole';"))
        labels = [row[0] for row in result.all()]
        print(f"UserRole enum labels in DB: {labels}")

if __name__ == "__main__":
    asyncio.run(check_enum())
