from models import HealthStatus


def check_health() -> HealthStatus:
    """Return a simple health payload."""

    return HealthStatus()


__all__ = ["check_health"]
