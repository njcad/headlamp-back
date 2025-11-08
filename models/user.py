from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    id: UUID
    created_at: datetime
    phone: Optional[str] = None
    email: Optional[str] = None


__all__ = ["User"]

