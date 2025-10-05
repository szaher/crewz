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


class Execution(BaseModel):
    """
    Execution model representing a flow or crew run.

    Tracks execution state, inputs, outputs, and references MongoDB logs.
    """

    __tablename__ = "executions"

    execution_type = Column(Enum(ExecutionType), nullable=False)
    status = Column(ExecutionStatus, nullable=False, default=ExecutionStatus.PENDING)

    # References
    flow_id = Column(Integer, ForeignKey("flows.id"), nullable=True, index=True)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Execution data
    input_data = Column(JSON, nullable=False, default=dict)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # MongoDB reference for detailed logs
    mongo_log_id = Column(String(24), nullable=True, index=True)

    # Relationships
    flow = relationship("Flow", back_populates="executions")
    user = relationship("User")

    def __repr__(self):
        return f"<Execution(id={self.id}, type={self.execution_type}, status={self.status})>"
