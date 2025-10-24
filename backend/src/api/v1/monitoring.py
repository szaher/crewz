"""
Monitoring dashboard API endpoints.

Provides aggregated metrics for LLM usage, costs, and performance.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ...db import get_db
from ...models.user import User
from ...models.trace_metrics import TraceMetrics, PeriodType
from ...api.middleware.auth import get_current_user
from ...services.metrics_aggregator import get_metrics_aggregator
from ...db.redis import get_redis_client


router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class MetricsByType(BaseModel):
    """Metrics breakdown by entity type."""
    count: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: int


class MetricsResponse(BaseModel):
    """Single period metrics response."""
    id: UUID
    tenant_id: UUID
    period_type: str
    period_start: datetime
    period_end: datetime
    total_executions: int
    total_traces: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: int
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    error_count: int
    error_rate: float
    metrics_by_type: Optional[dict] = None

    class Config:
        from_attributes = True


class MetricsListResponse(BaseModel):
    """List of metrics for dashboard."""
    metrics: List[MetricsResponse]
    period_type: str
    start_date: datetime
    end_date: datetime
    total_periods: int


class MetricsSummaryResponse(BaseModel):
    """Summary metrics for quick overview."""
    total_executions: int
    total_traces: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: int
    error_rate: float
    period_type: str
    date_range: str


# ============================================================================
# T039: GET /api/v1/monitoring/metrics - Dashboard metrics
# ============================================================================

@router.get("/metrics", response_model=MetricsListResponse)
async def get_metrics(
    period_type: str = Query(
        "day",
        regex="^(hour|day|week|month)$",
        description="Aggregation period type"
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Start date (default: 7 days ago for day, 24 hours ago for hour)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date (default: now)"
    ),
    entity_type: Optional[str] = Query(
        None,
        regex="^(crew|flow|agent|task|tool)$",
        description="Filter by entity type"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated metrics for monitoring dashboard.

    Returns pre-computed metrics with <5s response time (NFR-003).

    Period Types:
    - hour: Hourly aggregation (last 24 hours by default)
    - day: Daily aggregation (last 7 days by default)
    - week: Weekly aggregation (last 4 weeks by default)
    - month: Monthly aggregation (last 12 months by default)

    Metrics Include:
    - Total executions and traces
    - Token usage (prompt, completion, total)
    - Cost in USD
    - Latency percentiles (avg, P50, P95, P99)
    - Error rate
    - Breakdown by entity type (agent vs tool)
    """
    # Validate and convert period_type
    try:
        period_enum = PeriodType(period_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid period_type: {period_type}")

    # Set default date range based on period type
    if end_date is None:
        end_date = datetime.utcnow()

    if start_date is None:
        if period_enum == PeriodType.HOUR:
            start_date = end_date - timedelta(hours=24)
        elif period_enum == PeriodType.DAY:
            start_date = end_date - timedelta(days=7)
        elif period_enum == PeriodType.WEEK:
            start_date = end_date - timedelta(weeks=4)
        elif period_enum == PeriodType.MONTH:
            start_date = end_date - timedelta(days=365)

    # Get metrics aggregator service
    redis_client = get_redis_client()
    aggregator = get_metrics_aggregator(db, redis_client)

    # Query metrics (checks cache first, then database)
    metrics = aggregator.query_metrics(
        tenant_id=current_user.tenant_id,
        period_type=period_enum,
        start_date=start_date,
        end_date=end_date
    )

    # If metrics are cached, they're returned as dicts; if from DB, they're models
    # Convert to consistent format
    if metrics and isinstance(metrics[0], dict):
        # Already serialized from cache
        metrics_list = metrics
    else:
        # Serialize from models
        metrics_list = [aggregator._serialize_metrics(m) for m in metrics]

    # Filter by entity type if requested
    if entity_type and metrics_list:
        filtered_metrics = []
        for m in metrics_list:
            if m.get("metrics_by_type") and entity_type in m["metrics_by_type"]:
                filtered_metrics.append(m)
        metrics_list = filtered_metrics

    return MetricsListResponse(
        metrics=[MetricsResponse(**m) if isinstance(m, dict) else MetricsResponse.from_orm(m) for m in metrics_list],
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        total_periods=len(metrics_list)
    )


@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    period_type: str = Query(
        "day",
        regex="^(hour|day|week|month)$",
        description="Aggregation period type"
    ),
    days: int = Query(7, ge=1, le=365, description="Number of days to include in summary"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary metrics for quick dashboard overview.

    Returns aggregated totals across the specified time period.
    """
    # Validate period type
    try:
        period_enum = PeriodType(period_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid period_type: {period_type}")

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get metrics aggregator
    redis_client = get_redis_client()
    aggregator = get_metrics_aggregator(db, redis_client)

    # Query metrics
    metrics = aggregator.query_metrics(
        tenant_id=current_user.tenant_id,
        period_type=period_enum,
        start_date=start_date,
        end_date=end_date
    )

    # Aggregate totals
    total_executions = 0
    total_traces = 0
    total_tokens = 0
    total_cost_usd = 0.0
    total_latency = 0
    total_errors = 0
    count = 0

    for m in metrics:
        if isinstance(m, dict):
            total_executions += m.get("total_executions", 0)
            total_traces += m.get("total_traces", 0)
            total_tokens += m.get("total_tokens", 0)
            total_cost_usd += m.get("total_cost_usd", 0.0)
            total_latency += m.get("avg_latency_ms", 0)
            total_errors += m.get("error_count", 0)
            count += 1
        else:
            total_executions += m.total_executions
            total_traces += m.total_traces
            total_tokens += m.total_tokens
            total_cost_usd += float(m.total_cost_usd)
            total_latency += m.avg_latency_ms
            total_errors += m.error_count
            count += 1

    avg_latency = int(total_latency / count) if count > 0 else 0
    error_rate = round((total_errors / total_traces) * 100, 2) if total_traces > 0 else 0

    return MetricsSummaryResponse(
        total_executions=total_executions,
        total_traces=total_traces,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost_usd, 2),
        avg_latency_ms=avg_latency,
        error_rate=error_rate,
        period_type=period_type,
        date_range=f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    )


@router.get("/health")
async def monitoring_health():
    """Health check endpoint for monitoring service."""
    return {
        "status": "healthy",
        "service": "monitoring",
        "timestamp": datetime.utcnow().isoformat()
    }
