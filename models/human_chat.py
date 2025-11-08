from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class HumanChat(BaseModel):
    id: UUID
    user_id: UUID
    timestamp: datetime
    message: str


__all__ = ["HumanChat"]

