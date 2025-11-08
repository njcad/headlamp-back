from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    id: UUID
    created_at: datetime
    user_id: UUID
    question_id: UUID
    response: str


__all__ = ["QuestionResponse"]

