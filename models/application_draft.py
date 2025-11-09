from typing import Optional
from pydantic import BaseModel
from models.org import OrgSummary

class ApplicationDraft(BaseModel):
    """Single draft application that answers all intake questions for all selected organizations."""
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    summary: str  # Full application content with question/answer pairs
    organizations: list[OrgSummary]

__all__ = ["ApplicationDraft"]