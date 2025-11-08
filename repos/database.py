from supabase import Client, create_client

from config import settings


def get_supabase() -> Client:
    """Get a Supabase client."""
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("Supabase credentials not configured")
    
    return create_client(settings.supabase_url, settings.supabase_key)


__all__ = ["get_supabase"]

