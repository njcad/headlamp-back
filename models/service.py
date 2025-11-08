from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Service(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    intake_question_ids: list[int] = Field(default_factory=list)


__all__ = ["Service"]

