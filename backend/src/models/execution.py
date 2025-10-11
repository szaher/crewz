"""Execution model for flow and crew runs."""

from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Enum, Text
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class ExecutionStatus(str, enum.Enum):
    """Execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionType(str, enum.Enum):
    """Execution type enumeration."""

    FLOW = "flow"
    CREW = "crew"
    AGENT = "agent"
    TOOL = "tool"
    TASK = "task"


class Execution(BaseModel):
    """
    Execution model representing any type of execution (flow, crew, agent, tool, task).

    Tracks execution state, inputs, outputs, and references MongoDB logs.
    """

    __tablename__ = "executions"

    execution_type = Column(Enum(ExecutionType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    status = Column(Enum(ExecutionStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ExecutionStatus.PENDING.value)

    # References (nullable - only one will be populated based on type)
    flow_id = Column(Integer, ForeignKey("flows.id"), nullable=True, index=True)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    tool_id = Column(Integer, ForeignKey("tools.id"), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Execution data
    input_data = Column(JSON, nullable=False, default=dict)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Performance metrics
    execution_time_ms = Column(Integer, nullable=True)

    # MongoDB reference for detailed logs
    mongo_log_id = Column(String(24), nullable=True, index=True)

    # Relationships
    flow = relationship("Flow", back_populates="executions")
    user = relationship("User")

    def __repr__(self):
        return f"<Execution(id={self.id}, type={self.execution_type}, status={self.status})>"
