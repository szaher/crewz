"""Execution schemas for flow and crew runs."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionType(str, Enum):
    """Execution type enumeration."""

    FLOW = "flow"
    CREW = "crew"


class ExecutionCreate(BaseModel):
    """Create execution request schema."""

    execution_type: ExecutionType
    flow_id: Optional[int] = None
    crew_id: Optional[int] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResponse(BaseModel):
    """Execution response schema."""

    id: int
    execution_type: ExecutionType
    status: ExecutionStatus
    flow_id: Optional[int]
    crew_id: Optional[int]
    user_id: int
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """Execution list response schema."""

    executions: List[ExecutionResponse]
    total: int
    page: int
    page_size: int
