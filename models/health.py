from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str = "ok"
    service: str = "api"
    database: str = "unknown"


__all__ = ["HealthStatus"]
