"""
ExecutionQueue model for async task execution queue management.
Tracks execution requests through their lifecycle from pending to completion.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import BaseModel


class ExecutionStatus(str, enum.Enum):
    """Execution status states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecutionPriority(str, enum.Enum):
    """Execution priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ExecutionType(str, enum.Enum):
    """Types of entities that can be executed"""
    CREW = "crew"
    FLOW = "flow"
    AGENT = "agent"
    TASK = "task"
    TOOL = "tool"


class ExecutionQueue(BaseModel):
    """
    Async execution queue model.

    Tracks execution requests from submission through completion.
    Integrates with Celery for task processing via celery_task_id.

    State transitions:
    - pending → running → completed/failed/timeout
    - pending → cancelled
    - running → cancelled (if supported)
    """

    __tablename__ = "execution_queue"

    # Execution identification
    execution_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True,
                         comment="Public execution ID returned to client")

    # Tenant and user context
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Execution details
    execution_type = Column(Enum(ExecutionType), nullable=False,
                           comment="Type of entity being executed")
    entity_id = Column(UUID(as_uuid=True), nullable=False,
                      comment="ID of the crew/flow/agent/task/tool to execute")

    # Queue management
    status = Column(Enum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING, index=True)
    priority = Column(Enum(ExecutionPriority), nullable=False, default=ExecutionPriority.NORMAL, index=True)

    # Retry configuration
    retry_count = Column(Integer, nullable=False, default=0,
                        comment="Current retry attempt (0 = first attempt)")
    max_retries = Column(Integer, nullable=False, default=3,
                        comment="Maximum retry attempts before moving to DLQ")

    # Celery integration
    celery_task_id = Column(String(255), unique=True, nullable=True, index=True,
                           comment="Celery task ID for tracking and cancellation")

    # Execution payload and results
    payload = Column(JSON, nullable=False, default=dict,
                    comment="Execution parameters (inputs, config, etc.)")
    result = Column(JSON, nullable=True,
                   comment="Execution result (output, artifacts, etc.)")
    error = Column(String, nullable=True,
                  comment="Error message if execution failed")

    # Timestamps
    scheduled_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                         comment="When execution was submitted to queue")
    started_at = Column(DateTime, nullable=True,
                       comment="When execution actually started processing")
    completed_at = Column(DateTime, nullable=True,
                         comment="When execution finished (success or failure)")

    # Performance metrics
    duration_ms = Column(Integer, nullable=True,
                        comment="Execution duration in milliseconds")

    # Relationships
    tenant = relationship("Tenant", back_populates="executions")
    user = relationship("User", back_populates="executions")

    # Indexes for query optimization
    __table_args__ = (
        Index('idx_execution_queue_tenant_status', 'tenant_id', 'status'),
        Index('idx_execution_queue_status_priority', 'status', 'priority'),
        Index('idx_execution_queue_user_status', 'user_id', 'status'),
        Index('idx_execution_queue_scheduled_at', 'scheduled_at'),
    )

    def __repr__(self):
        return f"<ExecutionQueue(id={self.id}, execution_id={self.execution_id}, type={self.execution_type}, status={self.status})>"

    def can_cancel(self) -> bool:
        """Check if execution can be cancelled"""
        return self.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]

    def is_terminal_state(self) -> bool:
        """Check if execution is in a terminal state"""
        return self.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED
        ]

    def calculate_duration(self):
        """Calculate and set duration if started and completed"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
