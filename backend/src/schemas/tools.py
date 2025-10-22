"""Tool schemas for agent tools."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from uuid import UUID


class ToolType(str, Enum):
    """Tool type enumeration."""

    BUILTIN = "builtin"
    CUSTOM = "custom"
    DOCKER = "docker"


class ToolCreate(BaseModel):
    """Create tool request schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    tool_type: ToolType
    code: Optional[str] = None
    docker_image: Optional[str] = Field(None, max_length=255)
    docker_command: Optional[str] = Field(None, max_length=255)
    tool_schema: Dict[str, Any] = Field(default_factory=dict, alias='schema')


class ToolUpdate(BaseModel):
    """Update tool request schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    tool_type: Optional[ToolType] = None
    code: Optional[str] = None
    docker_image: Optional[str] = Field(None, max_length=255)
    docker_command: Optional[str] = Field(None, max_length=255)
    tool_schema: Optional[Dict[str, Any]] = Field(None, alias='schema')


class ToolResponse(BaseModel):
    """Tool response schema."""

    id: UUID
    name: str
    description: str
    tool_type: ToolType
    code: Optional[str]
    docker_image: Optional[str]
    docker_command: Optional[str]
    tool_schema: Dict[str, Any] = Field(..., alias='schema')
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow both 'tool_schema' and 'schema'


class ToolListResponse(BaseModel):
    """Tool list response schema."""

    tools: List[ToolResponse]
    total: int
    page: int
    page_size: int
