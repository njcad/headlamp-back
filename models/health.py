from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str = "ok"
    service: str = "api"


__all__ = ["HealthStatus"]
