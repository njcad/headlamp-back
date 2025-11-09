from fastapi import APIRouter

from .chat_routes import router as chat_router
from .health import router as health_router
from .application_routes import router as application_router

router = APIRouter()
router.include_router(health_router, prefix="/api", tags=["health"])
router.include_router(chat_router, prefix="/api", tags=["chat"])
router.include_router(application_router, prefix="/api", tags=["applications"])

__all__ = ["router"]
