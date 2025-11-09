from fastapi import APIRouter

from .chat_routes import router as chat_router
from .health import router as health_router

router = APIRouter()
router.include_router(health_router, prefix="/api", tags=["health"])
router.include_router(chat_router, prefix="/api", tags=["chat"])

__all__ = ["router"]
