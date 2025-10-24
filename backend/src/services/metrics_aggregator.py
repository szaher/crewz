"""
Metrics aggregation service for dashboard analytics.

Incrementally computes and caches trace metrics for fast dashboard loading.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
import statistics

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ..models.trace import Trace
from ..models.trace_metrics import TraceMetrics, PeriodType
from ..models.tenant_config import TenantConfig


logger = logging.getLogger(__name__)


class MetricsAggregator:
    """
    Service for computing aggregated metrics from traces.

    Features:
    - Incremental updates on trace ingestion
    - Percentile computation (P50, P95, P99)
    - Entity type breakdown
    - Redis caching with configurable TTL
    - <5s dashboard response time (NFR-003)
    """

    def __init__(self, db: Session, redis_client=None):
        """
        Initialize metrics aggregator.

        Args:
            db: Database session
            redis_client: Optional Redis client for caching
        """
        self.db = db
        self.redis_client = redis_client
        self.cache_prefix = "metrics:"


    def aggregate_trace_metrics(
        self,
        trace_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> None:
        """
        Incrementally update metrics after a new trace is ingested.

        Called asynchronously after trace creation.

        Args:
            trace_id: Trace UUID
            tenant_id: Optional tenant ID (fetched from trace if not provided)
        """
        # Get trace
        trace = self.db.query(Trace).filter(Trace.id == trace_id).first()
        if not trace:
            logger.warning(f"Trace {trace_id} not found for metrics aggregation")
            return

        if tenant_id is None:
            tenant_id = trace.tenant_id

        # Update metrics for all period types
        for period_type in PeriodType:
            self._update_period_metrics(trace, period_type)

        # Invalidate cache for this tenant
        self._invalidate_tenant_cache(tenant_id)

        logger.debug(f"Updated metrics for trace {trace_id}")


    def _update_period_metrics(self, trace: Trace, period_type: PeriodType):
        """
        Update metrics for a specific period type.

        Args:
            trace: Trace instance
            period_type: Period type (hour/day/week/month)
        """
        # Calculate period start/end
        period_start, period_end = self._get_period_boundaries(
            trace.created_at,
            period_type
        )

        # Get or create metrics record
        metrics = self.db.query(TraceMetrics).filter(
            and_(
                TraceMetrics.tenant_id == trace.tenant_id,
                TraceMetrics.period_type == period_type,
                TraceMetrics.period_start == period_start
            )
        ).first()

        if not metrics:
            metrics = TraceMetrics(
                tenant_id=trace.tenant_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                total_executions=0,
                total_traces=0,
                total_tokens=0,
                total_cost_usd=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                error_count=0,
                error_rate=0,
                metrics_by_type={}
            )
            self.db.add(metrics)

        # Increment counters
        metrics.total_traces += 1
        metrics.total_tokens += trace.total_tokens
        metrics.total_cost_usd += trace.cost_usd

        # Update error count
        if trace.error_message:
            metrics.error_count += 1

        # Recompute aggregated metrics (requires full query for accuracy)
        self._recompute_aggregated_metrics(metrics, period_start, period_end)

        self.db.commit()


    def _recompute_aggregated_metrics(
        self,
        metrics: TraceMetrics,
        period_start: datetime,
        period_end: datetime
    ):
        """
        Recompute aggregated metrics for a period.

        Args:
            metrics: TraceMetrics instance to update
            period_start: Period start time
            period_end: Period end time
        """
        # Query all traces in this period
        traces = self.db.query(Trace).filter(
            and_(
                Trace.tenant_id == metrics.tenant_id,
                Trace.created_at >= period_start,
                Trace.created_at < period_end
            )
        ).all()

        if not traces:
            return

        # Extract latencies for percentile computation
        latencies = [t.latency_ms for t in traces if t.latency_ms is not None]

        if latencies:
            # Compute percentiles
            sorted_latencies = sorted(latencies)
            metrics.avg_latency_ms = int(statistics.mean(sorted_latencies))
            metrics.p50_latency_ms = int(self._percentile(sorted_latencies, 50))
            metrics.p95_latency_ms = int(self._percentile(sorted_latencies, 95))
            metrics.p99_latency_ms = int(self._percentile(sorted_latencies, 99))

        # Compute error rate
        total_traces = len(traces)
        error_traces = sum(1 for t in traces if t.error_message is not None)
        metrics.error_rate = round((error_traces / total_traces) * 100, 2) if total_traces > 0 else 0

        # Count unique executions
        unique_executions = len(set(t.execution_id for t in traces if t.execution_id))
        metrics.total_executions = unique_executions

        # Breakdown by entity type (agent_id vs tool_id)
        metrics_by_type = {}

        # Count agent traces
        agent_traces = [t for t in traces if t.agent_id is not None]
        if agent_traces:
            metrics_by_type["agent"] = {
                "count": len(agent_traces),
                "total_tokens": sum(t.total_tokens for t in agent_traces),
                "total_cost_usd": float(sum(t.cost_usd for t in agent_traces)),
                "avg_latency_ms": int(statistics.mean([t.latency_ms for t in agent_traces if t.latency_ms]))
            }

        # Count tool traces
        tool_traces = [t for t in traces if t.tool_id is not None]
        if tool_traces:
            metrics_by_type["tool"] = {
                "count": len(tool_traces),
                "total_tokens": sum(t.total_tokens for t in tool_traces),
                "total_cost_usd": float(sum(t.cost_usd for t in tool_traces)),
                "avg_latency_ms": int(statistics.mean([t.latency_ms for t in tool_traces if t.latency_ms]))
            }

        metrics.metrics_by_type = metrics_by_type


    def _percentile(self, sorted_data: List[float], percentile: int) -> float:
        """
        Calculate percentile from sorted data.

        Args:
            sorted_data: Sorted list of numbers
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value
        """
        if not sorted_data:
            return 0

        k = (len(sorted_data) - 1) * (percentile / 100)
        f = int(k)
        c = f + 1

        if c >= len(sorted_data):
            return sorted_data[-1]

        d0 = sorted_data[f]
        d1 = sorted_data[c]

        return d0 + (d1 - d0) * (k - f)


    def _get_period_boundaries(
        self,
        timestamp: datetime,
        period_type: PeriodType
    ) -> tuple[datetime, datetime]:
        """
        Calculate period start/end boundaries.

        Args:
            timestamp: Timestamp to get period for
            period_type: Period type

        Returns:
            Tuple of (period_start, period_end)
        """
        if period_type == PeriodType.HOUR:
            period_start = timestamp.replace(minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)

        elif period_type == PeriodType.DAY:
            period_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)

        elif period_type == PeriodType.WEEK:
            # Week starts on Monday
            period_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            period_start -= timedelta(days=period_start.weekday())
            period_end = period_start + timedelta(days=7)

        elif period_type == PeriodType.MONTH:
            period_start = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Next month
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)

        else:
            raise ValueError(f"Invalid period type: {period_type}")

        return period_start, period_end


    def get_cached_metrics(
        self,
        tenant_id: UUID,
        period_type: PeriodType,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached metrics from Redis.

        Args:
            tenant_id: Tenant UUID
            period_type: Period type
            start_date: Start date
            end_date: End date

        Returns:
            List of metrics dicts or None if not cached
        """
        if not self.redis_client:
            return None

        cache_key = self._get_cache_key(tenant_id, period_type, start_date, end_date)

        try:
            import json
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for metrics: {cache_key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to retrieve cached metrics: {e}")

        return None


    def cache_metrics(
        self,
        tenant_id: UUID,
        period_type: PeriodType,
        start_date: datetime,
        end_date: datetime,
        metrics: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ):
        """
        Cache metrics in Redis.

        Args:
            tenant_id: Tenant UUID
            period_type: Period type
            start_date: Start date
            end_date: End date
            metrics: Metrics data to cache
            ttl: Cache TTL in seconds (default: retention_days + 7 days)
        """
        if not self.redis_client:
            return

        # Get TTL from tenant config
        if ttl is None:
            tenant_config = self.db.query(TenantConfig).filter(
                TenantConfig.tenant_id == tenant_id
            ).first()

            if tenant_config and tenant_config.trace_retention_days:
                ttl = (tenant_config.trace_retention_days + 7) * 86400  # Convert to seconds
            else:
                ttl = 14 * 86400  # Default 14 days

        cache_key = self._get_cache_key(tenant_id, period_type, start_date, end_date)

        try:
            import json
            self.redis_client.setex(cache_key, ttl, json.dumps(metrics))
            logger.debug(f"Cached metrics: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"Failed to cache metrics: {e}")


    def _get_cache_key(
        self,
        tenant_id: UUID,
        period_type: PeriodType,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Generate Redis cache key for metrics query."""
        return (
            f"{self.cache_prefix}{tenant_id}:"
            f"{period_type.value}:"
            f"{start_date.isoformat()}:"
            f"{end_date.isoformat()}"
        )


    def _invalidate_tenant_cache(self, tenant_id: UUID):
        """
        Invalidate all cached metrics for a tenant.

        Called after new trace ingestion.

        Args:
            tenant_id: Tenant UUID
        """
        if not self.redis_client:
            return

        try:
            # Find all cache keys for this tenant
            pattern = f"{self.cache_prefix}{tenant_id}:*"
            keys = self.redis_client.keys(pattern)

            if keys:
                self.redis_client.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} cache entries for tenant {tenant_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")


    def query_metrics(
        self,
        tenant_id: UUID,
        period_type: PeriodType,
        start_date: datetime,
        end_date: datetime
    ) -> List[TraceMetrics]:
        """
        Query metrics for a date range.

        Checks cache first, falls back to database.

        Args:
            tenant_id: Tenant UUID
            period_type: Period type
            start_date: Start date
            end_date: End date

        Returns:
            List of TraceMetrics instances
        """
        # Check cache first
        cached = self.get_cached_metrics(tenant_id, period_type, start_date, end_date)
        if cached:
            # Note: cached data is serialized, convert back to models if needed
            return cached

        # Query database
        metrics = self.db.query(TraceMetrics).filter(
            and_(
                TraceMetrics.tenant_id == tenant_id,
                TraceMetrics.period_type == period_type,
                TraceMetrics.period_start >= start_date,
                TraceMetrics.period_start < end_date
            )
        ).order_by(TraceMetrics.period_start).all()

        # Serialize for caching
        metrics_data = [self._serialize_metrics(m) for m in metrics]
        self.cache_metrics(tenant_id, period_type, start_date, end_date, metrics_data)

        return metrics


    def _serialize_metrics(self, metrics: TraceMetrics) -> Dict[str, Any]:
        """Serialize TraceMetrics to dict for caching."""
        return {
            "id": str(metrics.id),
            "tenant_id": str(metrics.tenant_id),
            "period_type": metrics.period_type.value,
            "period_start": metrics.period_start.isoformat(),
            "period_end": metrics.period_end.isoformat(),
            "total_executions": metrics.total_executions,
            "total_traces": metrics.total_traces,
            "total_tokens": metrics.total_tokens,
            "total_cost_usd": float(metrics.total_cost_usd),
            "avg_latency_ms": metrics.avg_latency_ms,
            "p50_latency_ms": metrics.p50_latency_ms,
            "p95_latency_ms": metrics.p95_latency_ms,
            "p99_latency_ms": metrics.p99_latency_ms,
            "error_count": metrics.error_count,
            "error_rate": float(metrics.error_rate),
            "metrics_by_type": metrics.metrics_by_type,
            "created_at": metrics.created_at.isoformat(),
            "updated_at": metrics.updated_at.isoformat()
        }


# Service factory function
def get_metrics_aggregator(db: Session, redis_client=None) -> MetricsAggregator:
    """Create metrics aggregator instance."""
    return MetricsAggregator(db, redis_client)
