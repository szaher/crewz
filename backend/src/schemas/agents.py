"""Agent schemas for CrewAI agents."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AgentCreate(BaseModel):
    """Create agent request schema."""

    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    goal: str = Field(..., min_length=1)
    backstory: str = Field(..., min_length=1)
    llm_provider_id: int
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    allow_delegation: bool = True
    verbose: bool = False
    tool_ids: List[int] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    """Update agent request schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    goal: Optional[str] = Field(None, min_length=1)
    backstory: Optional[str] = Field(None, min_length=1)
    llm_provider_id: Optional[int] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    allow_delegation: Optional[bool] = None
    verbose: Optional[bool] = None
    tool_ids: Optional[List[int]] = None


class AgentResponse(BaseModel):
    """Agent response schema."""

    id: int
    name: str
    role: str
    goal: str
    backstory: str
    llm_provider_id: int
    temperature: float
    max_tokens: Optional[int]
    allow_delegation: bool
    verbose: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Agent list response schema."""

    agents: List[AgentResponse]
    total: int
    page: int
    page_size: int
