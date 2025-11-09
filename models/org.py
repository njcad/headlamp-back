from pydantic import BaseModel


class OrgSummary(BaseModel):
    """
    Simplified organization model for API responses.
    Matches frontend OrgType - contains only essential fields.
    """
    id: int
    name: str
    description: str


__all__ = ["OrgSummary"]

