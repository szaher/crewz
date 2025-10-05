"""Tool model for agent tools."""

from sqlalchemy import Column, String, Text, JSON, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class ToolType(str, enum.Enum):
    """Tool type enumeration."""

    BUILTIN = "builtin"
    CUSTOM = "custom"
    DOCKER = "docker"


class Tool(BaseModel):
    """
    Tool model representing a tool that agents can use.

    Tools can be built-in CrewAI tools, custom Python code, or Docker containers.
    """

    __tablename__ = "tools"

    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    tool_type = Column(Enum(ToolType), nullable=False)

    # Tool implementation
    code = Column(Text, nullable=True)  # For custom Python tools
    docker_image = Column(String(255), nullable=True)  # For Docker tools
    docker_command = Column(String(255), nullable=True)

    # Tool schema (input parameters and return type)
    schema = Column(JSON, nullable=False, default=dict)

    # Relationships
    agents = relationship("Agent", secondary="agent_tools", back_populates="tools")

    def __repr__(self):
        return f"<Tool(id={self.id}, name={self.name}, type={self.tool_type})>"
