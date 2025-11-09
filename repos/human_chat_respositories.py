from datetime import datetime
from uuid import UUID

from models.human_chat import HumanChat
from repos.supabase import get_supabase_client


def get_by_user_id(user_id: UUID) -> list[HumanChat]:
    """Retrieve all human chat messages for a given user, sorted by timestamp."""
    client = get_supabase_client()
    
    response = (
        client.table("human_chats")
        .select("*")
        .eq("user_id", str(user_id))
        .order("timestamp", desc=False)
        .execute()
    )
    
    return [HumanChat(**row) for row in response.data]


def create(user_id: UUID, message: str) -> HumanChat:
    """Create a new human chat message."""
    client = get_supabase_client()
    
    data = {
        "user_id": str(user_id),
        "message": message,
    }
    
    response = client.table("human_chats").insert(data).execute()
    
    if not response.data:
        raise ValueError("Failed to create human chat message")
    
    return HumanChat(**response.data[0])


__all__ = ["get_by_user_id", "create"]

