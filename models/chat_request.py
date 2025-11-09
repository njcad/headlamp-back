from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model matching frontend UserMessagePayload."""
    user_id: Optional[UUID] = None
    message: str
    clickedOrgIds: Optional[list[int]] = None


__all__ = ["ChatRequest"]

