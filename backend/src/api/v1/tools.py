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
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get tool details by ID."""
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)
    return ToolResponse.from_orm(tool)


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: int,
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
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Delete a tool."""
    tool_service = ToolService(db)
    await tool_service.delete_tool(tool_id)


@router.post("/{tool_id}/execute")
async def execute_tool(
    tool_id: int,
    input_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Execute a tool directly with provided input.

    Executes the tool and returns the output.
    Supports custom Python tools and Docker tools.
    """
    import time
    tool_service = ToolService(db)
    tool = await tool_service.get_tool(tool_id)

    start_time = time.time()

    try:
        if tool.tool_type == "custom":
            # Execute custom Python tool directly
            import sys
            import os

            # Ensure user site-packages are in path (for pip install --user)
            import site
            user_site = site.getusersitepackages()
            if user_site not in sys.path:
                sys.path.insert(0, user_site)

            # Create a namespace with full access for tool execution
            # Tools are user-created, so we trust them in this context
            namespace = {
                '__builtins__': __builtins__,
                '__name__': '__main__',
                '__file__': '<tool>',
            }

            # Execute the tool code
            exec(tool.code, namespace)

            # Find the function in the namespace
            func_name = None
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith('_'):
                    func_name = name
                    break

            if not func_name:
                raise ValueError("No callable function found in tool code")

            func = namespace[func_name]

            # Execute with input_data
            if isinstance(input_data, dict):
                result = func(**input_data)
            else:
                result = func(input_data)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return {
                "tool_id": tool_id,
                "tool_name": tool.name,
                "tool_type": tool.tool_type,
                "input_data": input_data,
                "status": "success",
                "output": str(result),
                "execution_time_ms": execution_time_ms
            }

        elif tool.tool_type == "docker":
            # Execute Docker tool
            from ...services.docker_service import DockerService
            docker_service = DockerService()

            # Convert input to string for Docker
            import json
            input_str = json.dumps(input_data) if isinstance(input_data, dict) else str(input_data)

            result = await docker_service.execute_tool(
                tool_id=tool_id,
                input_data=input_str,
                docker_image=tool.docker_image,
                docker_command=tool.docker_command,
                timeout=30
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            return {
                "tool_id": tool_id,
                "tool_name": tool.name,
                "tool_type": tool.tool_type,
                "input_data": input_data,
                "status": "success",
                "output": result,
                "execution_time_ms": execution_time_ms
            }
        else:
            raise ValueError(f"Unsupported tool type: {tool.tool_type}")

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return {
            "tool_id": tool_id,
            "tool_name": tool.name,
            "tool_type": tool.tool_type,
            "input_data": input_data,
            "status": "failed",
            "error": str(e),
            "execution_time_ms": execution_time_ms
        }
