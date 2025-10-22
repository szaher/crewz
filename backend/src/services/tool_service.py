"""Tool service for agent tool management."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Tool
from ..schemas.tools import ToolCreate, ToolUpdate, ToolResponse, ToolListResponse
from .custom_tool_runner import CustomToolRunner
from .docker_service import DockerService


class ToolService:
    """Service for tool CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    async def create_tool(self, data: ToolCreate) -> Tool:
        """
        Create a new tool.

        Args:
            data: Tool creation data

        Returns:
            Created Tool model
        """
        # Validate tool type-specific fields
        if data.tool_type == "custom" and not data.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom tools require code",
            )

        if data.tool_type == "docker" and not data.docker_image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Docker tools require docker_image",
            )

        tool = Tool(
            name=data.name,
            description=data.description,
            tool_type=data.tool_type,
            code=data.code,
            docker_image=data.docker_image,
            docker_command=data.docker_command,
            schema=data.schema,
        )

        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)

        return tool

    async def get_tool(self, tool_id: int) -> Tool:
        """Get tool by ID."""
        tool = self.db.query(Tool).filter(Tool.id == tool_id).first()

        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found",
            )

        return tool

    async def list_tools(
        self, page: int = 1, page_size: int = 10, tool_type: Optional[str] = None
    ) -> ToolListResponse:
        """List tools with pagination and filtering."""
        query = self.db.query(Tool)

        if tool_type:
            query = query.filter(Tool.tool_type == tool_type)

        total = query.count()
        offset = (page - 1) * page_size
        tools = query.offset(offset).limit(page_size).all()

        return ToolListResponse(
            tools=[ToolResponse.from_orm(t) for t in tools],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_tool(self, tool_id: int, data: ToolUpdate) -> Tool:
        """Update an existing tool."""
        tool = await self.get_tool(tool_id)

        if data.name is not None:
            tool.name = data.name
        if data.description is not None:
            tool.description = data.description
        if data.tool_type is not None:
            tool.tool_type = data.tool_type
        if data.code is not None:
            tool.code = data.code
        if data.docker_image is not None:
            tool.docker_image = data.docker_image
        if data.docker_command is not None:
            tool.docker_command = data.docker_command
        if data.schema is not None:
            tool.schema = data.schema

        self.db.commit()
        self.db.refresh(tool)

        return tool

    async def delete_tool(self, tool_id: int) -> None:
        """Delete a tool."""
        tool = await self.get_tool(tool_id)
        self.db.delete(tool)
        self.db.commit()

    async def execute_tool(self, tool_id: UUID, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given input data.

        Args:
            tool_id: Tool UUID
            input_data: Input parameters for the tool

        Returns:
            Execution result with output and metadata

        Raises:
            HTTPException: If tool not found or execution fails
        """
        # Get tool from database
        tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_id}"
            )

        # Convert input_data to string for tool execution
        # Extract the actual parameter value from the input dict
        import json
        if isinstance(input_data, dict):
            # If dict has "input" or "value" key, use that
            if "input" in input_data:
                input_str = str(input_data["input"])
            elif "value" in input_data:
                input_str = str(input_data["value"])
            # If dict has single key-value pair, extract the value
            elif len(input_data) == 1:
                input_str = str(list(input_data.values())[0])
            # Otherwise, JSON stringify the whole dict
            else:
                input_str = json.dumps(input_data)
        else:
            input_str = str(input_data)

        # Execute based on tool type
        try:
            if tool.tool_type == "custom":
                # Execute custom Python tool
                if not tool.code:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Custom tool has no code defined"
                    )

                runner = CustomToolRunner(timeout=300)
                output = await runner.execute(tool.code, input_str)

                return {
                    "output": output,
                    "tool_id": str(tool_id),
                    "tool_name": tool.name,
                    "tool_type": tool.tool_type,
                    "status": "success"
                }

            elif tool.tool_type == "docker":
                # Execute Docker tool
                if not tool.docker_image:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Docker tool has no image defined"
                    )

                docker_service = DockerService()
                output = await docker_service.execute_tool(
                    tool_id=tool.id,
                    input_data=input_str,
                    docker_image=tool.docker_image,
                    docker_command=tool.docker_command,
                    timeout=300
                )

                return {
                    "output": output,
                    "tool_id": str(tool_id),
                    "tool_name": tool.name,
                    "tool_type": tool.tool_type,
                    "status": "success"
                }

            elif tool.tool_type == "builtin":
                # Builtin tools are handled by CrewAI framework
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Builtin tools cannot be executed directly. Use them within agents or crews."
                )

            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown tool type: {tool.tool_type}"
                )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tool execution failed: {str(e)}"
            )
