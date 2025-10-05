"""Crew schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CrewCreate(BaseModel):
    """Schema for creating a crew."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    process: str = "sequential"  # sequential or hierarchical
    verbose: bool = False
    agent_ids: List[int] = Field(default_factory=list)
    manager_llm_provider_id: Optional[int] = None


class CrewUpdate(BaseModel):
    """Schema for updating a crew."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    process: Optional[str] = None
    verbose: Optional[bool] = None
    agent_ids: Optional[List[int]] = None
    manager_llm_provider_id: Optional[int] = None


class CrewResponse(BaseModel):
    """Schema for crew response."""

    crew: dict

    class Config:
        from_attributes = True


class CrewListResponse(BaseModel):
    """Schema for list of crews."""

    crews: List[dict]
    total: int
