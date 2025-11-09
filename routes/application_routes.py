from fastapi import APIRouter
from uuid import UUID
from typing import Any

from models.application import Application
from services.application_service import ApplicationService

router = APIRouter()

@router.get("/applications")
async def get_user_applications(user_id: UUID) -> list[dict[str, Any]]:
    """
    Get all applications for a user with organization details.
    
    Returns list of dicts with 'application' and 'organization' keys.
    Each dict contains:
    - application: Application model
    - organization: OrgSummary model
    """
    return await ApplicationService.get_user_applications(user_id)

@router.get("/applications/{organization_id}")
async def get_organization_applications(organization_id: int) -> list[Application]:
    return await ApplicationService.get_organization_applications(organization_id)

__all__ = ["router"]