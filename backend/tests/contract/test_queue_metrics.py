"""
Contract tests for GET /api/v1/executions/queue/metrics endpoint.
Tests queue metrics according to execution-queue.openapi.yaml specification.
"""

import pytest
from fastapi.testclient import TestClient


class TestQueueMetrics:
    """Test GET /api/v1/executions/queue/metrics endpoint"""

    def test_get_queue_metrics_success(self, client: TestClient, auth_headers: dict):
        """Test get queue metrics with default timeframe"""
        response = client.get(
            "/api/v1/executions/queue/metrics",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Validate response schema
        data = response.json()
        assert "queue_depth" in data
        assert "pending_count" in data
        assert "running_count" in data
        assert "completed_last_minute" in data
        assert "failed_last_minute" in data
        assert "processing_rate" in data
        assert "avg_duration_ms" in data
        assert "p95_duration_ms" in data
        assert "p99_duration_ms" in data
        assert "failure_rate" in data
        assert "timestamp" in data

        # Validate data types
        assert isinstance(data["queue_depth"], int)
        assert isinstance(data["pending_count"], int)
        assert isinstance(data["running_count"], int)
        assert isinstance(data["processing_rate"], (int, float))
        assert isinstance(data["failure_rate"], (int, float))

        # Validate ranges
        assert data["queue_depth"] >= 0
        assert data["pending_count"] >= 0
        assert data["running_count"] >= 0
        assert 0.0 <= data["failure_rate"] <= 1.0

    def test_get_queue_metrics_all_timeframes(self, client: TestClient, auth_headers: dict):
        """Test queue metrics with different timeframes"""
        timeframes = ["1m", "5m", "15m", "1h", "24h"]

        for timeframe in timeframes:
            response = client.get(
                f"/api/v1/executions/queue/metrics?timeframe={timeframe}",
                headers=auth_headers
            )

            assert response.status_code == 200, f"Failed for timeframe: {timeframe}"
            data = response.json()
            assert "queue_depth" in data
            assert "timestamp" in data

    def test_get_queue_metrics_invalid_timeframe(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid timeframe"""
        response = client.get(
            "/api/v1/executions/queue/metrics?timeframe=invalid",
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    def test_get_queue_metrics_with_tenant_filter(self, client: TestClient, auth_headers: dict):
        """Test queue metrics filtered by tenant (admin only)"""
        from uuid import uuid4

        tenant_id = str(uuid4())

        response = client.get(
            f"/api/v1/executions/queue/metrics?tenant_id={tenant_id}",
            headers=auth_headers
        )

        # Should succeed for admin or return 403 for non-admin
        assert response.status_code in [200, 403]

    def test_get_queue_metrics_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        response = client.get("/api/v1/executions/queue/metrics")

        assert response.status_code == 401

    def test_get_queue_metrics_consistency(self, client: TestClient, auth_headers: dict):
        """Test queue depth equals pending + running"""
        response = client.get(
            "/api/v1/executions/queue/metrics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Queue depth should equal pending + running
        assert data["queue_depth"] == data["pending_count"] + data["running_count"]

    def test_get_queue_metrics_processing_rate(self, client: TestClient, auth_headers: dict):
        """Test processing rate is non-negative"""
        response = client.get(
            "/api/v1/executions/queue/metrics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Processing rate (tasks per second) should be >= 0
        assert data["processing_rate"] >= 0.0

    def test_get_queue_metrics_percentiles(self, client: TestClient, auth_headers: dict):
        """Test duration percentiles are ordered correctly"""
        response = client.get(
            "/api/v1/executions/queue/metrics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # p95 should be <= p99 (if both are non-zero)
        if data["p95_duration_ms"] > 0 and data["p99_duration_ms"] > 0:
            assert data["p95_duration_ms"] <= data["p99_duration_ms"]

        # avg should be <= p95 (if both are non-zero)
        if data["avg_duration_ms"] > 0 and data["p95_duration_ms"] > 0:
            assert data["avg_duration_ms"] <= data["p95_duration_ms"]
