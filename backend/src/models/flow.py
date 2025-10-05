"""Flow model for visual workflow orchestration."""

from sqlalchemy import Column, String, Text, JSON, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class FlowStatus(str, enum.Enum):
    """Flow status enumeration."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Flow(BaseModel):
    """
    Flow model representing a visual workflow with nodes and edges.

    Flows contain agents, tools, LLMs, conditions, inputs, and outputs
    connected via edges to define execution logic.
    """

    __tablename__ = "flows"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(FlowStatus), nullable=False, default=FlowStatus.DRAFT)

    # Flow definition (JSON structure for React Flow)
    nodes = Column(JSON, nullable=False, default=list)
    edges = Column(JSON, nullable=False, default=list)

    # Flow metadata
    version = Column(Integer, nullable=False, default=1)
    tags = Column(JSON, nullable=False, default=list)

    # Relationships
    executions = relationship(
        "Execution", back_populates="flow", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Flow(id={self.id}, name={self.name}, status={self.status}, version={self.version})>"
