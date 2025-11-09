from uuid import UUID, uuid4

from repos.supabase import get_supabase_client
from models.application import Application


def create(
    user_id: UUID,
    organization_id: int,
    content: str,
) -> Application:
    """Create a new application."""
    client = get_supabase_client()
    
    application_id = uuid4()
    
    data = {
        "id": str(application_id),
        "user_id": str(user_id),
        "organization_id": organization_id,
        "content": content,
        "urgent": False,
        # submitted_at is auto-populated by Supabase if default is set
    }
    
    response = client.table("applications").insert(data).execute()
    print(f"Application created: {response.data}")
    if not response.data:
        raise ValueError("Failed to create application")
    
    return Application(**response.data[0])

def get_by_user_id(user_id: UUID) -> list[Application]:
    """Get all applications for a user."""
    client = get_supabase_client()
    response = client.table("applications").select("*").eq("user_id", str(user_id)).execute()
    return [Application(**row) for row in response.data]

def get_by_organization_id(organization_id: int) -> list[Application]:
    """Get all applications for an organization."""
    client = get_supabase_client()
    response = client.table("applications").select("*").eq("organization_id", organization_id).execute()
    return [Application(**row) for row in response.data]


__all__ = ["create", "get_by_user_id", "get_by_organization_id"]

