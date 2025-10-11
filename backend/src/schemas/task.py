"""Task schemas for API validation."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from ..models.task import TaskOutputFormat


class TaskBase(BaseModel):
    """Base task schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)
    agent_id: Optional[int] = None
    crew_id: Optional[int] = None
    order: int = Field(default=0, ge=0)
    async_execution: bool = False
    output_format: TaskOutputFormat = TaskOutputFormat.TEXT
    output_file: Optional[str] = None
    context: Optional[str] = None
    tools_config: Optional[str] = None
    variables: Optional[List[str]] = None


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    expected_output: Optional[str] = Field(None, min_length=1)
    agent_id: Optional[int] = None
    crew_id: Optional[int] = None
    order: Optional[int] = Field(None, ge=0)
    async_execution: Optional[bool] = None
    output_format: Optional[TaskOutputFormat] = None
    output_file: Optional[str] = None
    context: Optional[str] = None
    tools_config: Optional[str] = None
    variables: Optional[List[str]] = None


class TaskResponse(TaskBase):
    """Schema for task response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for paginated task list response."""

    tasks: list[TaskResponse]
    total: int
    page: int = 1
    page_size: int = 10
