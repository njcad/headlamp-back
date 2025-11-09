from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

class Application(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: int
    urgent: bool
    content: str
    submitted_at: datetime
    opened_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    denied_at: Optional[datetime] = None
