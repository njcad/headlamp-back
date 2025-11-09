from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from models.org import OrgSummary


class ChatResponse(BaseModel):
    """Response model matching frontend AgentMessageResponse."""
    user_id: UUID
    message: str
    orgs: Optional[list[OrgSummary]] = None


__all__ = ["ChatResponse"]

