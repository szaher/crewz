"""TraceMetrics model for aggregated monitoring dashboard statistics."""

import enum
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, DateTime, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel


class PeriodType(str, enum.Enum):
    """Time period type for metrics aggregation."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TraceMetrics(BaseModel):
    """
    TraceMetrics model for pre-computed aggregated statistics.

    Used for fast dashboard loading without real-time aggregation.
    Updated incrementally as new traces arrive.
    """

    __tablename__ = "trace_metrics"

    # Foreign keys
    tenant_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Time period
    period_type = Column(postgresql.ENUM(PeriodType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # Aggregations
    total_executions = Column(Integer, nullable=False, default=0)
    total_traces = Column(Integer, nullable=False, default=0)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    total_cost_usd = Column(postgresql.NUMERIC(12, 2), nullable=False, default=0)

    # Performance metrics
    avg_latency_ms = Column(Integer, nullable=False, default=0)
    p50_latency_ms = Column(Integer, nullable=False, default=0)
    p95_latency_ms = Column(Integer, nullable=False, default=0)
    p99_latency_ms = Column(Integer, nullable=False, default=0)

    # Error tracking
    error_count = Column(Integer, nullable=False, default=0)
    error_rate = Column(postgresql.NUMERIC(5, 2), nullable=False, default=0)  # Percentage

    # Breakdown by entity type (crew, agent, tool, flow)
    metrics_by_type = Column(postgresql.JSONB, nullable=True)

    # Indexes and constraints
    __table_args__ = (
        Index("idx_metrics_tenant_period", "tenant_id", "period_type", "period_start"),
        UniqueConstraint("tenant_id", "period_type", "period_start", name="uq_metrics_tenant_period_start"),

        # Constraints
        CheckConstraint("period_end > period_start", name="chk_metrics_period_valid"),
        CheckConstraint("total_tokens >= 0", name="chk_metrics_tokens_non_negative"),
        CheckConstraint("total_cost_usd >= 0", name="chk_metrics_cost_non_negative"),
        CheckConstraint("error_rate >= 0 AND error_rate <= 100", name="chk_metrics_error_rate_range"),
    )

    def __repr__(self):
        return (
            f"<TraceMetrics(id={self.id}, tenant_id={self.tenant_id}, "
            f"period={self.period_type.value}, traces={self.total_traces})>"
        )
