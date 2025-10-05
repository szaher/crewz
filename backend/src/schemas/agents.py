"""Agent schemas for CrewAI agents."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AgentCreate(BaseModel):
    """Create agent request schema matching CrewAI Agent fields."""

    # Required fields
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    role: str = Field(..., min_length=1, max_length=255, description="Agent role (e.g., 'Senior Data Analyst')")
    goal: str = Field(..., min_length=1, description="Agent's goal")
    backstory: str = Field(..., min_length=1, description="Agent's backstory")

    # LLM configuration
    llm_provider_id: int = Field(..., description="LLM provider ID")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens for LLM")

    # Agent behavior
    allow_delegation: bool = Field(default=True, description="Allow task delegation to other agents")
    verbose: bool = Field(default=False, description="Enable verbose logging")
    cache: bool = Field(default=True, description="Enable caching")
    max_iter: int = Field(default=15, ge=1, description="Maximum iterations for task execution")
    max_rpm: Optional[int] = Field(None, gt=0, description="Maximum requests per minute")
    max_execution_time: Optional[int] = Field(None, gt=0, description="Maximum execution time in seconds")

    # Advanced features
    allow_code_execution: bool = Field(default=False, description="Allow code execution")
    respect_context_window: bool = Field(default=True, description="Respect LLM context window")
    max_retry_limit: int = Field(default=2, ge=0, description="Maximum retry attempts")

    # Tools
    tool_ids: List[int] = Field(default_factory=list, description="Tool IDs")


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
    cache: Optional[bool] = None
    max_iter: Optional[int] = Field(None, ge=1)
    max_rpm: Optional[int] = Field(None, gt=0)
    max_execution_time: Optional[int] = Field(None, gt=0)
    allow_code_execution: Optional[bool] = None
    respect_context_window: Optional[bool] = None
    max_retry_limit: Optional[int] = Field(None, ge=0)
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
    cache: bool
    max_iter: int
    max_rpm: Optional[int]
    max_execution_time: Optional[int]
    allow_code_execution: bool
    respect_context_window: bool
    max_retry_limit: int
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
