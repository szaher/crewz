"""
Trace persistence service for storing LLM execution traces.

Persists trace data from Langfuse callbacks to PostgreSQL for monitoring dashboard.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.trace import Trace, TraceMetrics


class TraceService:
    """Service for persisting and querying LLM execution traces."""

    def __init__(self, db: Session):
        self.db = db

    async def create_trace(self, trace_data: Dict[str, Any]) -> Trace:
        """
        Create a new trace record.

        Args:
            trace_data: Trace data from Langfuse callback handler

        Returns:
            Created Trace model
        """
        trace = Trace(
            trace_id=trace_data["trace_id"],
            execution_id=UUID(trace_data["execution_id"]),
            tenant_id=UUID(trace_data["tenant_id"]),
            agent_id=UUID(trace_data["agent_id"]) if trace_data.get("agent_id") else None,
            tool_id=UUID(trace_data["tool_id"]) if trace_data.get("tool_id") else None,
            model_name=trace_data["model_name"],
            provider=trace_data["provider"],
            prompt=trace_data["prompt"],
            response=trace_data.get("response", ""),
            prompt_tokens=trace_data.get("prompt_tokens", 0),
            completion_tokens=trace_data.get("completion_tokens", 0),
            total_tokens=trace_data.get("total_tokens", 0),
            cost_usd=trace_data.get("cost_usd", 0.0),
            latency_ms=trace_data.get("latency_ms", 0),
            error_message=trace_data.get("error_message"),
            start_time=trace_data["start_time"],
            end_time=trace_data.get("end_time"),
        )

        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)

        return trace

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        return self.db.query(Trace).filter(Trace.trace_id == trace_id).first()

    async def get_execution_traces(
        self,
        execution_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Trace]:
        """
        Get all traces for an execution.

        Args:
            execution_id: Execution UUID
            limit: Maximum number of traces to return
            offset: Pagination offset

        Returns:
            List of Trace models
        """
        return (
            self.db.query(Trace)
            .filter(Trace.execution_id == execution_id)
            .order_by(Trace.start_time.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    async def get_tenant_traces(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Trace]:
        """
        Get traces for a tenant with optional date filtering.

        Args:
            tenant_id: Tenant UUID
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of traces to return
            offset: Pagination offset

        Returns:
            List of Trace models
        """
        query = self.db.query(Trace).filter(Trace.tenant_id == tenant_id)

        if start_date:
            query = query.filter(Trace.start_time >= start_date)
        if end_date:
            query = query.filter(Trace.start_time <= end_date)

        return (
            query
            .order_by(Trace.start_time.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    async def aggregate_metrics(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "day"  # day, hour, execution, agent, model
    ) -> List[Dict[str, Any]]:
        """
        Aggregate trace metrics for dashboard display.

        Args:
            tenant_id: Tenant UUID
            start_date: Start date for aggregation
            end_date: End date for aggregation
            group_by: Grouping strategy (day, hour, execution, agent, model)

        Returns:
            List of aggregated metrics
        """
        query = self.db.query(
            func.count(Trace.id).label("call_count"),
            func.sum(Trace.prompt_tokens).label("total_prompt_tokens"),
            func.sum(Trace.completion_tokens).label("total_completion_tokens"),
            func.sum(Trace.total_tokens).label("total_tokens"),
            func.sum(Trace.cost_usd).label("total_cost_usd"),
            func.avg(Trace.latency_ms).label("avg_latency_ms"),
            func.count(func.nullif(Trace.error_message, None)).label("error_count"),
        ).filter(
            Trace.tenant_id == tenant_id,
            Trace.start_time >= start_date,
            Trace.start_time <= end_date
        )

        # Add grouping
        if group_by == "execution":
            query = query.add_columns(Trace.execution_id.label("group_key"))
            query = query.group_by(Trace.execution_id)
        elif group_by == "agent":
            query = query.add_columns(Trace.agent_id.label("group_key"))
            query = query.group_by(Trace.agent_id)
        elif group_by == "model":
            query = query.add_columns(Trace.model_name.label("group_key"))
            query = query.group_by(Trace.model_name)
        elif group_by == "day":
            # PostgreSQL-specific date_trunc
            query = query.add_columns(func.date_trunc('day', Trace.start_time).label("group_key"))
            query = query.group_by(func.date_trunc('day', Trace.start_time))
        elif group_by == "hour":
            query = query.add_columns(func.date_trunc('hour', Trace.start_time).label("group_key"))
            query = query.group_by(func.date_trunc('hour', Trace.start_time))

        results = query.all()

        metrics = []
        for row in results:
            metrics.append({
                "group_key": str(row.group_key) if hasattr(row, "group_key") else None,
                "call_count": row.call_count,
                "total_prompt_tokens": row.total_prompt_tokens or 0,
                "total_completion_tokens": row.total_completion_tokens or 0,
                "total_tokens": row.total_tokens or 0,
                "total_cost_usd": float(row.total_cost_usd or 0.0),
                "avg_latency_ms": float(row.avg_latency_ms or 0.0),
                "error_count": row.error_count or 0,
            })

        return metrics

    async def delete_old_traces(self, tenant_id: UUID, retention_days: int) -> int:
        """
        Delete traces older than retention period.

        Args:
            tenant_id: Tenant UUID
            retention_days: Number of days to retain traces

        Returns:
            Number of traces deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        deleted = (
            self.db.query(Trace)
            .filter(
                Trace.tenant_id == tenant_id,
                Trace.start_time < cutoff_date
            )
            .delete()
        )

        self.db.commit()

        return deleted

    async def create_or_update_trace_metrics(
        self,
        execution_id: UUID,
        metrics_data: Dict[str, Any]
    ) -> TraceMetrics:
        """
        Create or update aggregated metrics for an execution.

        Args:
            execution_id: Execution UUID
            metrics_data: Aggregated metrics data

        Returns:
            Created or updated TraceMetrics model
        """
        # Check if metrics already exist
        existing = (
            self.db.query(TraceMetrics)
            .filter(TraceMetrics.execution_id == execution_id)
            .first()
        )

        if existing:
            # Update existing metrics
            for key, value in metrics_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new metrics
            metrics = TraceMetrics(
                execution_id=execution_id,
                **metrics_data
            )
            self.db.add(metrics)
            self.db.commit()
            self.db.refresh(metrics)
            return metrics

    async def get_execution_metrics(self, execution_id: UUID) -> Optional[TraceMetrics]:
        """Get aggregated metrics for an execution."""
        return (
            self.db.query(TraceMetrics)
            .filter(TraceMetrics.execution_id == execution_id)
            .first()
        )

    async def compute_and_save_execution_metrics(self, execution_id: UUID) -> TraceMetrics:
        """
        Compute aggregated metrics from traces and save to TraceMetrics table.

        Args:
            execution_id: Execution UUID

        Returns:
            Created or updated TraceMetrics model
        """
        # Aggregate traces for this execution
        traces = await self.get_execution_traces(execution_id, limit=10000)

        total_calls = len(traces)
        total_prompt_tokens = sum(t.prompt_tokens for t in traces)
        total_completion_tokens = sum(t.completion_tokens for t in traces)
        total_tokens = sum(t.total_tokens for t in traces)
        total_cost_usd = sum(t.cost_usd for t in traces)
        avg_latency_ms = sum(t.latency_ms for t in traces) / total_calls if total_calls > 0 else 0
        error_count = sum(1 for t in traces if t.error_message)

        # Compute percentiles (simple approach)
        latencies = sorted([t.latency_ms for t in traces])
        p50_latency_ms = latencies[len(latencies) // 2] if latencies else 0
        p95_latency_ms = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99_latency_ms = latencies[int(len(latencies) * 0.99)] if latencies else 0

        metrics_data = {
            "total_calls": total_calls,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
            "avg_latency_ms": avg_latency_ms,
            "p50_latency_ms": p50_latency_ms,
            "p95_latency_ms": p95_latency_ms,
            "p99_latency_ms": p99_latency_ms,
            "error_count": error_count,
        }

        return await self.create_or_update_trace_metrics(execution_id, metrics_data)


# Missing import for timedelta
from datetime import timedelta
