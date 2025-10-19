"""Execution model for flow and crew runs."""

import enum
import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Enum, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel


class ExecutionStatus(str, enum.Enum):
    """Execution status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"  # Added for worker architecture - execution in queue
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
    flow_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("flows.id"), nullable=True, index=True)
    crew_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("crews.id"), nullable=True, index=True)
    agent_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True)
    tool_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tools.id"), nullable=True, index=True)
    task_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    user_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Execution data
    input_data = Column(JSON, nullable=False, default=dict)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Performance metrics
    execution_time_ms = Column(Integer, nullable=True)

    # MongoDB reference for detailed logs
    mongo_log_id = Column(String(24), nullable=True, index=True)

    # ===== Worker Architecture Fields (Phase 004) =====
    # All fields nullable for backward compatibility
    priority = Column(Integer, nullable=True, default=5, index=True)  # 1-10, lower is higher priority
    queue_position = Column(Integer, nullable=True)  # Position in queue (ephemeral, tracked in Redis)
    retry_count = Column(Integer, nullable=True, default=0)  # Number of retry attempts
    timeout_seconds = Column(Integer, nullable=True, default=600)  # Execution timeout (10 min default)
    parent_execution_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("executions.id"), nullable=True, index=True)  # For re-executions
    artifact_version = Column(Integer, nullable=True, default=1)  # Artifact version number
    cancellation_requested = Column(sa.Boolean, nullable=True, default=False)  # Graceful cancellation flag
    worker_id = Column(String(255), nullable=True, index=True)  # Worker instance ID that processed this execution

    # Relationships
    flow = relationship("Flow", back_populates="executions")
    user = relationship("User")
    parent_execution = relationship("Execution", remote_side="Execution.id", foreign_keys=[parent_execution_id])
    artifacts = relationship("ExecutionArtifact", back_populates="execution", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Execution(id={self.id}, type={self.execution_type}, status={self.status})>"
