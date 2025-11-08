from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IntakeQuestion(BaseModel):
    id: int
    created_at: datetime
    question: str


__all__ = ["IntakeQuestion"]

