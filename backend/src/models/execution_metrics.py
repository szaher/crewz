"""
ExecutionMetrics model for queue performance tracking.
Stores time-series metrics for monitoring queue health and performance.
"""

from sqlalchemy import Column, Integer, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel


class ExecutionMetrics(BaseModel):
    """
    Time-series metrics for execution queue monitoring.

    Stores aggregated metrics at regular intervals (e.g., every minute)
    for dashboard visualizations and performance analysis.

    Note: Consider using TimescaleDB hypertable for production deployments
    with high metric volume. For basic deployments, regular PostgreSQL
    table with time-based partitioning is sufficient.
    """

    __tablename__ = "execution_metrics"

    # Time dimension
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True,
                      comment="Metric collection timestamp")

    # Tenant dimension (for multi-tenant metrics)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True,
                      comment="Tenant ID (null for global metrics)")

    # Queue depth metrics
    queue_depth = Column(Integer, nullable=False, default=0,
                        comment="Total pending + running executions")
    pending_count = Column(Integer, nullable=False, default=0,
                          comment="Executions in pending state")
    running_count = Column(Integer, nullable=False, default=0,
                          comment="Executions in running state")

    # Throughput metrics
    completed_last_minute = Column(Integer, nullable=False, default=0,
                                  comment="Executions completed in last minute")
    failed_last_minute = Column(Integer, nullable=False, default=0,
                               comment="Executions failed in last minute")
    processing_rate = Column(Float, nullable=False, default=0.0,
                            comment="Tasks per second")

    # Performance metrics
    avg_duration_ms = Column(Integer, nullable=False, default=0,
                            comment="Average execution duration (milliseconds)")
    p95_duration_ms = Column(Integer, nullable=False, default=0,
                            comment="95th percentile duration (milliseconds)")
    p99_duration_ms = Column(Integer, nullable=False, default=0,
                            comment="99th percentile duration (milliseconds)")

    # Quality metrics
    failure_rate = Column(Float, nullable=False, default=0.0,
                         comment="Failure rate (0.0-1.0)")

    # Indexes for time-series queries
    __table_args__ = (
        Index('idx_execution_metrics_timestamp', 'timestamp'),
        Index('idx_execution_metrics_tenant_timestamp', 'tenant_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<ExecutionMetrics(timestamp={self.timestamp}, queue_depth={self.queue_depth}, tenant={self.tenant_id})>"

    @classmethod
    def calculate_from_executions(cls, executions: list, tenant_id=None) -> dict:
        """
        Calculate metrics from a list of execution records.

        Args:
            executions: List of ExecutionQueue objects
            tenant_id: Optional tenant ID for tenant-specific metrics

        Returns:
            Dict of metric values ready for model creation
        """
        from statistics import mean, quantiles

        pending = [e for e in executions if e.status == "pending"]
        running = [e for e in executions if e.status == "running"]
        completed = [e for e in executions if e.status == "completed"]
        failed = [e for e in executions if e.status == "failed"]

        # Duration metrics (only from completed/failed executions)
        durations = [e.duration_ms for e in executions
                    if e.duration_ms is not None and e.duration_ms > 0]

        avg_duration = int(mean(durations)) if durations else 0

        # Calculate percentiles (p95, p99)
        if len(durations) >= 2:
            try:
                percentiles = quantiles(durations, n=100)  # 99 percentiles
                p95_duration = int(percentiles[94])  # 95th percentile (0-indexed)
                p99_duration = int(percentiles[98])  # 99th percentile
            except:
                p95_duration = max(durations) if durations else 0
                p99_duration = max(durations) if durations else 0
        else:
            p95_duration = max(durations) if durations else 0
            p99_duration = max(durations) if durations else 0

        # Failure rate
        total_terminal = len(completed) + len(failed)
        failure_rate = len(failed) / total_terminal if total_terminal > 0 else 0.0

        # Processing rate (tasks per second) - approximate
        # This should be calculated based on timeframe, here we approximate
        processing_rate = len(completed) / 60.0  # Assuming 1-minute window

        return {
            "timestamp": datetime.utcnow(),
            "tenant_id": tenant_id,
            "queue_depth": len(pending) + len(running),
            "pending_count": len(pending),
            "running_count": len(running),
            "completed_last_minute": len(completed),
            "failed_last_minute": len(failed),
            "processing_rate": round(processing_rate, 2),
            "avg_duration_ms": avg_duration,
            "p95_duration_ms": p95_duration,
            "p99_duration_ms": p99_duration,
            "failure_rate": round(failure_rate, 4)
        }
