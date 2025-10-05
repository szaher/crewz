"""Adapter for converting database tools to CrewAI tools."""

from typing import Any, Callable
from crewai.tools import BaseTool as CrewAITool, tool

from ..models import Tool
from ..services.docker_service import DockerService


class ToolAdapter:
    """Adapter to convert database Tool models to CrewAI Tool instances."""

    def __init__(self, docker_service: DockerService):
        self.docker_service = docker_service

    async def from_db_model(self, tool: Tool) -> CrewAITool:
        """
        Create a CrewAI Tool from database model.

        Args:
            tool: Database Tool model

        Returns:
            CrewAI Tool instance
        """
        if tool.tool_type == "builtin":
            # Built-in CrewAI tools - import dynamically
            return self._get_builtin_tool(tool.name)

        elif tool.tool_type == "custom":
            # Custom Python code tool
            func = self._create_custom_tool_func(tool.code)
            # Use @tool decorator for newer crewai versions
            return tool(name=tool.name, description=tool.description)(func)

        elif tool.tool_type == "docker":
            # Docker container tool
            async def docker_func(input_data: str) -> str:
                return await self.docker_service.execute_tool(
                    tool_id=tool.id,
                    input_data=input_data,
                    docker_image=tool.docker_image,
                    docker_command=tool.docker_command,
                )

            # Use @tool decorator for newer crewai versions
            return tool(name=tool.name, description=tool.description)(docker_func)

        else:
            raise ValueError(f"Unknown tool type: {tool.tool_type}")

    def _get_builtin_tool(self, tool_name: str) -> CrewAITool:
        """Get built-in CrewAI tool by name."""
        # Import built-in tools from CrewAI
        from crewai.tools import (
            SerperDevTool,
            WebsiteSearchTool,
            FileReadTool,
            DirectoryReadTool,
        )

        tool_map = {
            "serper_search": SerperDevTool,
            "website_search": WebsiteSearchTool,
            "file_read": FileReadTool,
            "directory_read": DirectoryReadTool,
        }

        if tool_name not in tool_map:
            raise ValueError(f"Unknown built-in tool: {tool_name}")

        return tool_map[tool_name]()

    def _create_custom_tool_func(self, code: str) -> Callable:
        """
        Create a function from custom Python code.

        Args:
            code: Python code for the tool function

        Returns:
            Callable function

        Note: This uses exec() which is dangerous for untrusted code.
        In production, should run in isolated environment.
        """
        # Create namespace
        namespace = {}

        # Execute code to define function
        exec(code, namespace)

        # Find the tool function (convention: must be named 'run')
        if "run" not in namespace:
            raise ValueError("Custom tool code must define a 'run' function")

        return namespace["run"]
