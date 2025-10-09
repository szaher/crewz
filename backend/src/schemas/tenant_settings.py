"""Schemas for tenant settings endpoints."""

from pydantic import BaseModel, Field, conint


class TenantSettingsResponse(BaseModel):
    id: int
    name: str
    schema_name: str
    status: str
    max_users: int
    max_agents: int
    max_flows: int
    settings: dict | None = None


class TenantSettingsUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    max_users: conint(ge=1) | None = None
    max_agents: conint(ge=1) | None = None
    max_flows: conint(ge=1) | None = None
    settings: dict | None = None
