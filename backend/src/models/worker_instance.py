"""Worker instance model for tracking Celery worker health and status."""

import enum
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime, Float, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel


class WorkerStatus(str, enum.Enum):
    """Worker status enumeration."""

    STARTING = "starting"  # Worker initializing
    IDLE = "idle"  # Worker registered and ready for tasks
    BUSY = "busy"  # Worker currently processing a task
    CRASHED = "crashed"  # Worker failed to send heartbeat
    STOPPED = "stopped"  # Worker gracefully shut down


class WorkerInstance(BaseModel):
    """
    Worker instance model for tracking Celery worker pool.

    Tracks worker health via heartbeats, current job assignment,
    and resource usage for monitoring and autoscaling decisions.
    """

    __tablename__ = "worker_instances"

    # Worker identification (unique hostname from Celery worker)
    worker_hostname = Column(String(255), nullable=False, unique=True, index=True)  # e.g., "celery@worker1"

    # Worker status
    status = Column(
        Enum(WorkerStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=WorkerStatus.STARTING.value,
        index=True
    )

    # Current job assignment
    current_job_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Resource usage metrics (for autoscaling and monitoring)
    cpu_usage_percent = Column(Float, nullable=True)  # Current CPU usage (0-100%)
    memory_usage_mb = Column(Integer, nullable=True)  # Current memory usage in MB

    # Health tracking
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Last heartbeat timestamp
    crashed_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp when marked as crashed

    # Relationships
    current_job = relationship("Execution", foreign_keys=[current_job_id])

    # Unique constraint on worker_hostname
    __table_args__ = (
        UniqueConstraint('worker_hostname', name='uq_worker_hostname'),
    )

    def __repr__(self):
        return f"<WorkerInstance(id={self.id}, hostname={self.worker_hostname}, status={self.status})>"

    def is_healthy(self, timeout_seconds: int = 90) -> bool:
        """
        Check if worker is healthy based on heartbeat.

        Args:
            timeout_seconds: Maximum seconds since last heartbeat (default 90s)

        Returns:
            True if heartbeat is recent, False if stale
        """
        if self.status == WorkerStatus.CRASHED:
            return False

        if not self.last_heartbeat_at:
            return False

        time_since_heartbeat = datetime.utcnow() - self.last_heartbeat_at
        return time_since_heartbeat.total_seconds() <= timeout_seconds

    def update_heartbeat(self, cpu_percent: float = None, memory_mb: int = None) -> None:
        """
        Update worker heartbeat and resource metrics.

        Args:
            cpu_percent: Current CPU usage percentage (0-100)
            memory_mb: Current memory usage in MB
        """
        self.last_heartbeat_at = datetime.utcnow()
        if cpu_percent is not None:
            self.cpu_usage_percent = cpu_percent
        if memory_mb is not None:
            self.memory_usage_mb = memory_mb

        # Reset crash status if worker recovers
        if self.status == WorkerStatus.CRASHED:
            self.status = WorkerStatus.IDLE
            self.crashed_at = None

    def mark_as_crashed(self) -> None:
        """Mark worker as crashed due to missing heartbeat."""
        if self.status != WorkerStatus.CRASHED:
            self.status = WorkerStatus.CRASHED
            self.crashed_at = datetime.utcnow()

    def assign_job(self, execution_id) -> None:
        """
        Assign job to worker.

        Args:
            execution_id: UUID of execution to assign
        """
        self.current_job_id = execution_id
        self.status = WorkerStatus.BUSY

    def release_job(self) -> None:
        """Release current job from worker."""
        self.current_job_id = None
        self.status = WorkerStatus.IDLE

    @classmethod
    def get_healthy_workers(cls, db_session) -> list:
        """
        Get all healthy workers from database.

        Args:
            db_session: SQLAlchemy session

        Returns:
            List of healthy WorkerInstance objects
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=90)
        return db_session.query(cls).filter(
            cls.status.in_([WorkerStatus.IDLE, WorkerStatus.BUSY]),
            cls.last_heartbeat_at >= cutoff_time
        ).all()

    @classmethod
    def get_idle_workers(cls, db_session) -> list:
        """
        Get all idle workers available for new tasks.

        Args:
            db_session: SQLAlchemy session

        Returns:
            List of idle WorkerInstance objects
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=90)
        return db_session.query(cls).filter(
            cls.status == WorkerStatus.IDLE,
            cls.last_heartbeat_at >= cutoff_time
        ).all()
