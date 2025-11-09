from datetime import datetime
from typing import Any
from uuid import UUID

from models.agent_chat import AgentChat
from repos.supabase import get_supabase_client


def get_by_user_id(user_id: UUID) -> list[AgentChat]:
    """Retrieve all agent chat messages for a given user, sorted by timestamp."""
    client = get_supabase_client()
    
    response = (
        client.table("agent_chats")
        .select("*")
        .eq("user_id", str(user_id))
        .order("timestamp", desc=False)
        .execute()
    )
    
    return [AgentChat(**row) for row in response.data]


def create(
    user_id: UUID,
    message: str,
    model: str,
    tool_calls: list[dict[str, Any]] | None = None,
) -> AgentChat:
    """Create a new agent chat message."""
    client = get_supabase_client()
    
    data = {
        "user_id": str(user_id),
        "message": message,
        "model": model,
    }
    
    if tool_calls is not None:
        data["tool_calls"] = tool_calls
    
    response = client.table("agent_chats").insert(data).execute()
    
    if not response.data:
        raise ValueError("Failed to create agent chat message")
    
    return AgentChat(**response.data[0])


__all__ = ["get_by_user_id", "create"]

