"""Tool API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ...schemas.tools import (
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolListResponse,
)
from ...services.tool_service import ToolService
from ...api.middleware.auth import require_auth

router = APIRouter()


@router.get("", response_model=ToolListResponse)
async def list_tools(
    page: int = 1,
    page_size: int = 10,
    tool_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List tools with pagination and filtering.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10, max: 100)
    - **tool_type**: Filter by type (builtin, custom, docker)
    """
    if page_size > 100:
        page_size = 100

    tool_service = ToolService(db)
    return await tool_service.list_tools(
        page=page,
        page_size=page_size,
        tool_type=tool_type,
    )


@router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    request: ToolCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new tool.

    - **name**: Tool name
    - **description**: Tool description
    - **tool_type**: Tool type (builtin, custom, docker)
    - **code**: Python code (for custom tools)
    - **docker_image**: Docker image (for docker tools)
    - **docker_command**: Docker command (for docker tools)
    - **schema**: Input/output schema
    """
    tool_service = ToolService(db)
    tool = await tool_service.create_tool(request)
    return ToolResponse.from_orm(tool)


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get tool details by ID."""
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)
    return ToolResponse.from_orm(tool)


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    request: ToolUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update an existing tool."""
    tool_service = ToolService(db)
    tool = await tool_service.update_tool(tool_id, request)
    return ToolResponse.from_orm(tool)


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Delete a tool."""
    tool_service = ToolService(db)
    await tool_service.delete_tool(tool_id)


@router.post("/{tool_id}/execute")
async def execute_tool(
    tool_id: str,
    input_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Execute a tool asynchronously.

    Returns immediately with execution ID and status "queued".
    The execution happens on workers in the background.

    Supports custom Python tools and Docker tools.
    """
    from uuid import UUID
    from ...services.execution_service_worker import ExecutionServiceWorker
    from ...config.settings import Settings

    # Get tool for name
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    # Initialize worker service which handles both worker and legacy execution paths
    settings = Settings()
    execution_service_worker = ExecutionServiceWorker(
        db_session=db,
        settings=settings
    )

    # Queue the execution (will use workers if enabled, otherwise falls back to legacy)
    user_id = current_user.get("id")
    execution = execution_service_worker.queue_execution(
        execution_type="tool",
        entity_id=UUID(tool_id),
        input_params=input_data,
        user_id=user_id if isinstance(user_id, UUID) else UUID(user_id),
        priority=5,
        timeout_seconds=600
    )

    return {
        "execution_id": str(execution.id),
        "tool_id": tool_id,
        "tool_name": tool.name,
        "tool_type": tool.tool_type,
        "input_data": input_data,
        "status": execution.status.value,
        "message": "Execution queued on workers. Check execution status for results."
    }
