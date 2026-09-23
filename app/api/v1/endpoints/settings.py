from fastapi import APIRouter

from app.api.dependencies import CurrentActiveCashierDep, DbDep
from app.schemas.business_settings import BusinessSettingsRead, BusinessSettingsUpdate
from app.services.business_settings_service import business_settings_service

router = APIRouter()


@router.get("", response_model=BusinessSettingsRead)
async def get_business_settings(db: DbDep):
    """Public business info (name, address, phone) for the landing page and header."""
    return await business_settings_service.get_settings(db)


@router.put("", response_model=BusinessSettingsRead)
async def update_business_settings(
    settings_in: BusinessSettingsUpdate,
    db: DbDep,
    staff: CurrentActiveCashierDep,
):
    """Update business settings (Cashier, Manager or Owner)."""
    return await business_settings_service.update_settings(db, settings_in)