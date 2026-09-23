from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.models.business_settings import BusinessSettings
from app.repositories.business_settings_repository import business_settings_repo

logger = get_logger(__name__)


class BusinessSettingsService:
    async def get_settings(self, db: AsyncSession) -> BusinessSettings:
        """Returns the business settings, creating the default row if missing."""
        settings = await business_settings_repo.get_settings(db)
        if settings is None:
            settings = BusinessSettings(
                id=1,
                name="Bowling SaaS",
                address="Calle 123, Centro Ciudad",
                phone="+1 (555) 123-4567",
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings

    async def update_settings(
        self, db: AsyncSession, obj_in: dict | BusinessSettings
    ) -> BusinessSettings:
        """Updates the single business settings row."""
        settings = await self.get_settings(db)
        updated = await business_settings_repo.update(db, db_obj=settings, obj_in=obj_in)
        logger.info("Business settings updated")
        return updated


business_settings_service = BusinessSettingsService()