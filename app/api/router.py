from fastapi import APIRouter
from app.api.v1.endpoints import auth, bookings, admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])