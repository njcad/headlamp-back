from fastapi import APIRouter

from models import HealthStatus
from services import check_health

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Report basic service health."""

    return check_health()


__all__ = ["router"]
