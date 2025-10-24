"""Integration test for dashboard metrics performance <5s (Scenario 3 from quickstart.md)."""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import time
import random


@pytest.mark.asyncio
async def test_dashboard_metrics_performance_under_5s(
    authed_client: AsyncClient,
    test_tenant_id: str
):
    """
    Test Scenario 3: Dashboard Metrics Performance.

    Given: 100 executions with traces over 7 days
    When: Dashboard metrics endpoint is queried
    Then: Response time is <5s (NFR-003) and data is correct
    """
    # Arrange: Seed 100 executions with traces over 7 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    print(f"Seeding 100 executions over 7 days...")
    await seed_executions_with_traces(
        authed_client,
        tenant_id=test_tenant_id,
        count=100,
        start_date=start_date,
        end_date=end_date
    )

    # Act: Query metrics endpoint and measure response time
    query_start = time.time()

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    query_duration = time.time() - query_start

    # Assert: Response time <5s (NFR-003)
    assert response.status_code == 200
    assert query_duration < 5.0, (
        f"Dashboard metrics query took {query_duration:.2f}s, exceeds 5s limit (NFR-003)"
    )

    # Assert: Verify response structure
    data = response.json()
    assert "metrics" in data
    assert "summary" in data

    metrics = data["metrics"]
    summary = data["summary"]

    # Should have metrics for up to 7 daily periods
    assert len(metrics) <= 7
    assert len(metrics) > 0

    # Verify metrics structure
    for metric in metrics:
        assert "period_type" in metric
        assert metric["period_type"] == "day"
        assert "period_start" in metric
        assert "period_end" in metric
        assert "total_executions" in metric
        assert "total_traces" in metric
        assert "total_tokens" in metric
        assert "total_cost_usd" in metric
        assert "avg_latency_ms" in metric
        assert "p50_latency_ms" in metric
        assert "p95_latency_ms" in metric
        assert "p99_latency_ms" in metric
        assert "error_count" in metric
        assert "error_rate" in metric

    # Verify summary structure
    assert "total_cost_usd" in summary
    assert "total_tokens" in summary
    assert "avg_cost_per_execution" in summary
    assert "trend" in summary
    assert summary["trend"] in ["increasing", "decreasing", "stable"]

    # Verify data correctness (total executions should be ~100)
    total_executions = sum(m["total_executions"] for m in metrics)
    assert 95 <= total_executions <= 105, f"Expected ~100 executions, got {total_executions}"

    print(f"✓ Dashboard metrics query completed in {query_duration:.2f}s (<5s requirement)")


@pytest.mark.asyncio
async def test_metrics_aggregation_by_period_type(
    authed_client: AsyncClient,
    test_tenant_id: str
):
    """Test metrics aggregation for different period types (hour, day, week, month)."""
    # Seed some executions
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    await seed_executions_with_traces(
        authed_client,
        tenant_id=test_tenant_id,
        count=50,
        start_date=start_date,
        end_date=end_date
    )

    # Test each period type
    for period_type in ["hour", "day", "week", "month"]:
        # Adjust date range based on period type
        if period_type == "hour":
            query_start = end_date - timedelta(hours=24)
        elif period_type == "day":
            query_start = end_date - timedelta(days=7)
        elif period_type == "week":
            query_start = end_date - timedelta(weeks=4)
        else:  # month
            query_start = end_date - timedelta(days=90)

        response = await authed_client.get(
            "/api/v1/monitoring/metrics",
            params={
                "period_type": period_type,
                "start_date": query_start.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all metrics have correct period_type
        for metric in data["metrics"]:
            assert metric["period_type"] == period_type


@pytest.mark.asyncio
async def test_metrics_entity_type_breakdown(
    authed_client: AsyncClient,
    test_tenant_id: str
):
    """Test that metrics include breakdown by entity type (crew, agent, tool, flow)."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    await seed_executions_with_traces(
        authed_client,
        tenant_id=test_tenant_id,
        count=20,
        start_date=start_date,
        end_date=end_date
    )

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == 200
    metrics = response.json()["metrics"]

    # Check if metrics_by_type is present
    for metric in metrics:
        if metric.get("metrics_by_type"):
            metrics_by_type = metric["metrics_by_type"]

            # Should have breakdown for different entity types
            for entity_type in ["crew", "agent", "tool", "flow"]:
                if entity_type in metrics_by_type:
                    entity_metrics = metrics_by_type[entity_type]
                    assert "count" in entity_metrics
                    assert "tokens" in entity_metrics
                    assert "cost_usd" in entity_metrics
                    assert "avg_latency_ms" in entity_metrics


@pytest.mark.asyncio
async def test_metrics_with_entity_type_filter(
    authed_client: AsyncClient,
    test_tenant_id: str
):
    """Test filtering metrics by specific entity type."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    await seed_executions_with_traces(
        authed_client,
        tenant_id=test_tenant_id,
        count=20,
        start_date=start_date,
        end_date=end_date
    )

    for entity_type in ["crew", "agent", "tool", "flow", "all"]:
        response = await authed_client.get(
            "/api/v1/monitoring/metrics",
            params={
                "period_type": "day",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "entity_type": entity_type
            }
        )

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_percentile_calculations(
    authed_client: AsyncClient,
    test_tenant_id: str
):
    """Test that latency percentiles (P50, P95, P99) are calculated correctly."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)

    await seed_executions_with_traces(
        authed_client,
        tenant_id=test_tenant_id,
        count=30,
        start_date=start_date,
        end_date=end_date
    )

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == 200
    metrics = response.json()["metrics"]

    for metric in metrics:
        p50 = metric["p50_latency_ms"]
        p95 = metric["p95_latency_ms"]
        p99 = metric["p99_latency_ms"]
        avg = metric["avg_latency_ms"]

        # Percentiles should be in increasing order
        assert p50 <= p95 <= p99, f"Percentiles not in order: P50={p50}, P95={p95}, P99={p99}"

        # Average should be between P50 and P95 typically
        assert p50 <= avg, f"Average {avg} is less than P50 {p50}"


@pytest.mark.asyncio
async def test_metrics_error_rate_calculation(
    authed_client: AsyncClient,
    test_tenant_id: str
):
    """Test that error rate is calculated correctly."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)

    # Seed some executions with traces (some with errors)
    await seed_executions_with_traces(
        authed_client,
        tenant_id=test_tenant_id,
        count=20,
        start_date=start_date,
        end_date=end_date,
        error_rate=0.1  # 10% error rate
    )

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == 200
    metrics = response.json()["metrics"]

    for metric in metrics:
        error_rate = metric["error_rate"]

        # Error rate should be between 0 and 100
        assert 0 <= error_rate <= 100

        # If there are traces with errors, error_rate should be > 0
        if metric["error_count"] > 0:
            assert error_rate > 0


# Helper function
async def seed_executions_with_traces(
    client: AsyncClient,
    tenant_id: str,
    count: int,
    start_date: datetime,
    end_date: datetime,
    error_rate: float = 0.0
):
    """
    Seed test executions with traces.

    This is a placeholder that would create test data.
    In real implementation, this would:
    1. Create executions in the database
    2. Create traces for each execution
    3. Distribute them across the date range
    4. Include some errors based on error_rate
    """
    # NOTE: This is a test helper that would need to be implemented
    # to directly insert data into the database for testing purposes.
    # For now, it's a placeholder that represents the seeding logic.

    time_delta = (end_date - start_date).total_seconds() / count

    for i in range(count):
        # Calculate execution time
        execution_time = start_date + timedelta(seconds=i * time_delta)

        # Create execution via API or direct DB insert
        # This would need actual implementation
        pass

    # Give the system time to process
    import asyncio
    await asyncio.sleep(1)
