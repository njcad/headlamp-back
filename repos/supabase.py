from functools import lru_cache

from supabase import Client, create_client

from config import settings


@lru_cache
def get_supabase_client() -> Client:
    """Return a cached Supabase client instance."""

    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("Supabase credentials are not configured.")

    return create_client(settings.supabase_url, settings.supabase_key)


__all__ = ["get_supabase_client"]
