from typing import Optional

from pydantic import BaseModel

from models.org import OrgSummary


class ChatResponse(BaseModel):
    """Response model matching frontend AgentMessageResponse."""
    message: str
    orgs: Optional[list[OrgSummary]] = None


__all__ = ["ChatResponse"]

