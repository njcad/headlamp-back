from fastapi import APIRouter
from uuid import UUID

from models.application import Application
from services.application_service import ApplicationService

router = APIRouter()

@router.get("/applications")
async def get_user_applications(user_id: UUID) -> list[Application]:
    return await ApplicationService.get_user_applications(user_id)

@router.get("/applications/{organization_id}")
async def get_organization_applications(organization_id: int) -> list[Application]:
    return await ApplicationService.get_organization_applications(organization_id)

__all__ = ["router"]