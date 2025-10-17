"""
DeadLetterTask model for failed task management.
Stores tasks that have exhausted all retry attempts for manual inspection and requeue.
"""

from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel


class DeadLetterTask(BaseModel):
    """
    Dead Letter Queue (DLQ) model.

    Stores execution tasks that have failed after all retry attempts.
    Provides retry history for debugging and allows manual requeue.
    """

    __tablename__ = "dead_letter_tasks"

    # Reference to original execution
    original_queue_id = Column(UUID(as_uuid=True), ForeignKey("execution_queue.id"), nullable=False, index=True,
                              comment="ID of the original execution_queue record")

    # Execution details (denormalized for easy access)
    execution_type = Column(String(50), nullable=False,
                           comment="Type of execution (crew, flow, agent, task, tool)")
    payload = Column(JSON, nullable=False,
                    comment="Original execution payload")

    # Failure information
    failure_reason = Column(String, nullable=False,
                           comment="Final error message that caused DLQ entry")
    retry_history = Column(JSON, nullable=False, default=list,
                          comment="Array of retry attempts with timestamps, errors, durations")

    # Timestamps
    failure_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow,
                              comment="When task was moved to DLQ")

    # Requeue status
    is_requeued = Column(Boolean, nullable=False, default=False, index=True,
                        comment="Whether task has been manually requeued")

    # Relationships
    original_execution = relationship("ExecutionQueue", foreign_keys=[original_queue_id])

    def __repr__(self):
        return f"<DeadLetterTask(id={self.id}, execution_type={self.execution_type}, is_requeued={self.is_requeued})>"

    def add_to_retry_history(self, attempt: int, error: str, duration_ms: int, timestamp: datetime = None):
        """
        Add a retry attempt to the history.

        Args:
            attempt: Retry attempt number (1-based)
            error: Error message
            duration_ms: Execution duration in milliseconds
            timestamp: When the attempt occurred (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        if self.retry_history is None:
            self.retry_history = []

        self.retry_history.append({
            "attempt": attempt,
            "timestamp": timestamp.isoformat(),
            "error": error,
            "duration_ms": duration_ms
        })

    def get_retry_count(self) -> int:
        """Get total number of retry attempts"""
        return len(self.retry_history) if self.retry_history else 0

    def get_last_error(self) -> str:
        """Get the error message from the last retry attempt"""
        if self.retry_history and len(self.retry_history) > 0:
            return self.retry_history[-1].get("error", "Unknown error")
        return self.failure_reason
