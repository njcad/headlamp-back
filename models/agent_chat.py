from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentChat(BaseModel):
    id: UUID
    timestamp: datetime
    model: str
    message: str
    tool_calls: list[dict[str, Any]] | None = Field(default=None, description="JSON payload of tool calls")


__all__ = ["AgentChat"]

