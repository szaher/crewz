"""Contract test for GET /api/v1/monitoring/metrics endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_get_metrics_daily_success(authed_client: AsyncClient):
    """Test successful retrieval of daily metrics."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema per traces-api.yaml
    data = response.json()
    assert "metrics" in data
    assert "summary" in data
    assert isinstance(data["metrics"], list)


@pytest.mark.asyncio
async def test_get_metrics_hourly(authed_client: AsyncClient):
    """Test hourly metrics aggregation."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=24)

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "hour",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_metrics_weekly(authed_client: AsyncClient):
    """Test weekly metrics aggregation."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(weeks=4)

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "week",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_metrics_monthly(authed_client: AsyncClient):
    """Test monthly metrics aggregation."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=90)

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "month",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_metrics_trace_metrics_schema(authed_client: AsyncClient):
    """Test that TraceMetrics schema matches traces-api.yaml."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    if len(data["metrics"]) > 0:
        metric = data["metrics"][0]

        # Required fields per TraceMetrics schema
        assert "id" in metric
        assert "tenant_id" in metric
        assert "period_type" in metric
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

        # Value constraints
        assert metric["total_executions"] >= 0
        assert metric["total_traces"] >= 0
        assert metric["total_tokens"] >= 0
        assert metric["total_cost_usd"] >= 0
        assert 0 <= metric["error_rate"] <= 100
        assert metric["period_type"] in ["hour", "day", "week", "month"]


@pytest.mark.asyncio
async def test_get_metrics_with_entity_type_filter(authed_client: AsyncClient):
    """Test filtering metrics by entity type."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

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

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_metrics_by_type_breakdown(authed_client: AsyncClient):
    """Test that metrics_by_type includes entity breakdown."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    if len(data["metrics"]) > 0 and data["metrics"][0].get("metrics_by_type"):
        metrics_by_type = data["metrics"][0]["metrics_by_type"]

        # Check EntityMetrics schema for each type
        for entity_type in ["crew", "agent", "tool", "flow"]:
            if entity_type in metrics_by_type:
                entity_metrics = metrics_by_type[entity_type]
                assert "count" in entity_metrics
                assert "tokens" in entity_metrics
                assert "cost_usd" in entity_metrics
                assert "avg_latency_ms" in entity_metrics


@pytest.mark.asyncio
async def test_get_metrics_summary_schema(authed_client: AsyncClient):
    """Test that MetricsSummary schema matches specification."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    summary = data["summary"]
    assert "total_cost_usd" in summary
    assert "total_tokens" in summary
    assert "avg_cost_per_execution" in summary
    assert "trend" in summary

    # Validate trend enum
    assert summary["trend"] in ["increasing", "decreasing", "stable"]


@pytest.mark.asyncio
async def test_get_metrics_missing_required_params(authed_client: AsyncClient):
    """Test 400 response when required parameters are missing."""
    # Missing period_type
    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_metrics_invalid_period_type(authed_client: AsyncClient):
    """Test 400 response for invalid period_type."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "invalid",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_metrics_invalid_date_range(authed_client: AsyncClient):
    """Test 400 response when end_date is before start_date."""
    end_date = datetime.utcnow()
    start_date = end_date + timedelta(days=7)  # Start after end

    response = await authed_client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_metrics_unauthorized(client: AsyncClient):
    """Test that endpoint requires authentication."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    response = await client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
