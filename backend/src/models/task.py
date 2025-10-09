"""Task model for CrewAI tasks."""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class TaskOutputFormat(str, enum.Enum):
    """Task output format enumeration."""

    TEXT = "text"
    JSON = "json"
    PYDANTIC = "pydantic"


class Task(BaseModel):
    """
    Task model representing a CrewAI task configuration.

    Tasks are assigned to agents and can be part of crews.
    Similar to CrewAI's Task object with description, expected_output, and agent assignment.
    """

    __tablename__ = "tasks"

    # Task identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)

    # Agent assignment
    agent_id = Column(
        Integer, ForeignKey("agents.id"), nullable=True, index=True
    )

    # Crew association
    crew_id = Column(
        Integer, ForeignKey("crews.id"), nullable=True, index=True
    )

    # Task ordering within crew
    order = Column(Integer, nullable=False, default=0)

    # Task configuration
    async_execution = Column(Boolean, nullable=False, default=False)
    output_format = Column(Enum(TaskOutputFormat), nullable=False, default=TaskOutputFormat.TEXT)
    output_file = Column(String(500), nullable=True)
    context = Column(Text, nullable=True)

    # Tool configuration
    tools_config = Column(Text, nullable=True)  # JSON string of tool-specific configs

    # Relationships
    agent = relationship("Agent", backref="tasks")
    crew = relationship("Crew", backref="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, name={self.name}, agent_id={self.agent_id}, crew_id={self.crew_id})>"
