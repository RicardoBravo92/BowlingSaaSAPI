from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_settings import BusinessSettings
from app.repositories.base_repository import BaseRepository


class BusinessSettingsRepository(BaseRepository[BusinessSettings]):
    async def get_settings(self, db: AsyncSession) -> BusinessSettings | None:
        """Fetches the single settings row (id = 1)."""
        result = await db.execute(select(self.model).where(self.model.id == 1))
        return result.scalar_one_or_none()


business_settings_repo = BusinessSettingsRepository(BusinessSettings)