"""Flow schemas for visual workflow orchestration."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class FlowStatus(str, Enum):
    """Flow status enumeration."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class NodeData(BaseModel):
    """Flow node data schema."""

    id: str
    type: str  # "agent" | "tool" | "llm" | "condition" | "input" | "output"
    position: Dict[str, float]  # {"x": 100, "y": 200}
    data: Dict[str, Any]  # Node-specific configuration


class EdgeData(BaseModel):
    """Flow edge data schema."""

    id: str
    source: str  # Source node ID
    target: str  # Target node ID
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    label: Optional[str] = None


class FlowCreate(BaseModel):
    """Create flow request schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    nodes: List[NodeData] = Field(default_factory=list)
    edges: List[EdgeData] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class FlowUpdate(BaseModel):
    """Update flow request schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[FlowStatus] = None
    nodes: Optional[List[NodeData]] = None
    edges: Optional[List[EdgeData]] = None
    tags: Optional[List[str]] = None


class FlowResponse(BaseModel):
    """Flow response schema."""

    id: int
    name: str
    description: Optional[str]
    status: FlowStatus
    nodes: List[NodeData]
    edges: List[EdgeData]
    version: int
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FlowListResponse(BaseModel):
    """Flow list response schema."""

    flows: List[FlowResponse]
    total: int
    page: int
    page_size: int
