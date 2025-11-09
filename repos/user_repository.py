from typing import Optional
from uuid import UUID, uuid4

from models.user import User
from repos.supabase import get_supabase_client


def get_by_id(user_id: UUID) -> Optional[User]:
    """Fetch a user by id. Returns None if not found."""
    client = get_supabase_client()
    response = (
        client.table("users")
        .select("*")
        .eq("id", str(user_id))
        .execute()
    )
    if not response.data:
        return None
    return User(**response.data[0])


def create_with_id(user_id: UUID) -> User:
    """Create a user with a specific id. Id must be a UUID."""
    client = get_supabase_client()
    response = client.table("users").insert({"id": str(user_id)}).execute()
    if not response.data:
        raise ValueError("Failed to create user")
    return User(**response.data[0])

def create() -> User:
    """Create a user with a freshly generated UUID (server-side)."""
    new_id = uuid4()
    return create_with_id(new_id)


def ensure_exists(user_id: UUID) -> User:
    """Return user if exists; otherwise create it."""
    existing = get_by_id(user_id)
    if existing:
        return existing
    return create_with_id(user_id)


__all__ = ["get_by_id", "create_with_id", "ensure_exists"]


