from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, get_current_active_owner
from app.models import User

router = APIRouter()

@router.patch("/slots/{slot_id}")
async def update_slot_price(
    slot_id: int,
    new_price: float,
    db: AsyncSession = Depends(get_db),
    current_owner: User = Depends(get_current_active_owner) 
):
    return {"message": "Precio actualizado correctamente"}      