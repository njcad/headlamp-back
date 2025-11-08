from fastapi import APIRouter

from .health import router as health_router

router = APIRouter()
router.include_router(health_router, prefix="/api", tags=["health"])

__all__ = ["router"]
