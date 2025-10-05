"""Tool schemas for agent tools."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


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
    schema: Dict[str, Any] = Field(default_factory=dict)


class ToolUpdate(BaseModel):
    """Update tool request schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    tool_type: Optional[ToolType] = None
    code: Optional[str] = None
    docker_image: Optional[str] = Field(None, max_length=255)
    docker_command: Optional[str] = Field(None, max_length=255)
    schema: Optional[Dict[str, Any]] = None


class ToolResponse(BaseModel):
    """Tool response schema."""

    id: int
    name: str
    description: str
    tool_type: ToolType
    code: Optional[str]
    docker_image: Optional[str]
    docker_command: Optional[str]
    schema: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """Tool list response schema."""

    tools: List[ToolResponse]
    total: int
    page: int
    page_size: int
