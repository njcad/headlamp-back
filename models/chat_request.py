from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from models.application_draft import ApplicationDraft


class ChatRequest(BaseModel):
    """Request model matching frontend UserMessagePayload."""
    user_id: Optional[UUID] = None
    message: str
    clickedOrgIds: Optional[list[int]] = None
    applicationDraft: Optional[ApplicationDraft] = None
    doApply: Optional[list[int]] = None


__all__ = ["ChatRequest"]

