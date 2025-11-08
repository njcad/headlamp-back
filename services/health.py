from models import HealthStatus
from repos import get_supabase


def check_health() -> HealthStatus:
    """Return a simple health payload with database status."""
    db_status = "unknown"
    
    try:
        supabase = get_supabase()
        # Simple query to test connection
        supabase.table("services").select("id").limit(1).execute()
        db_status = "connected"
    except RuntimeError:
        db_status = "not_configured"
    except Exception:
        db_status = "error"
    
    return HealthStatus(database=db_status)


__all__ = ["check_health"]
