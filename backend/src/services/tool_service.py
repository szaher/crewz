"""Tool service for agent tool management."""

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Tool
from ..schemas.tools import ToolCreate, ToolUpdate, ToolResponse, ToolListResponse


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
