"""Crew schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from ..models.crew import CrewProcess


class CrewCreate(BaseModel):
    """Schema for creating a crew."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    process: CrewProcess = CrewProcess.SEQUENTIAL
    verbose: bool = False
    memory: bool = False
    agent_ids: List[int] = Field(default_factory=list)
    manager_llm_provider_id: Optional[int] = None
    # Compatibility with older frontend payloads
    process_type: Optional[CrewProcess] = None
    agents: Optional[List[int]] = None


class CrewUpdate(BaseModel):
    """Schema for updating a crew."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    process: Optional[CrewProcess] = None
    verbose: Optional[bool] = None
    memory: Optional[bool] = None
    agent_ids: Optional[List[int]] = None
    manager_llm_provider_id: Optional[int] = None
    # Compatibility with older frontend payloads
    process_type: Optional[CrewProcess] = None
    agents: Optional[List[int]] = None


class CrewOut(BaseModel):
    """Schema representing a crew."""

    id: int
    name: str
    description: Optional[str] = None
    process: CrewProcess
    verbose: bool
    memory: bool
    manager_llm_provider_id: Optional[int] = None
    agent_ids: List[int] = []
    task_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CrewResponse(BaseModel):
    crew: CrewOut


class CrewListResponse(BaseModel):
    crews: List[CrewOut]
    total: int
