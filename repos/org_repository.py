from repos.supabase import get_supabase_client
from models.service import Organization


def get_all() -> list[Organization]:
    """Retrieve all organizations from the database."""
    print("Getting all organizations")
    client = get_supabase_client()
    
    response = client.table("services").select("*").execute()
    
    return [Organization(**row) for row in response.data]


def get_by_ids(org_ids: list[int]) -> list[Organization]:
    """Retrieve organizations by their IDs."""
    print(f"Getting organizations by IDs: {org_ids}")
    client = get_supabase_client()
    
    response = (
        client.table("services")
        .select("*")
        .in_("id", org_ids)
        .execute()
    )
    
    return [Organization(**row) for row in response.data]


__all__ = ["get_all", "get_by_ids"]

