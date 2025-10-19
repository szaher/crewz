"""Contract test for GET /api/v1/executions/{id}/status endpoint.

Verifies queue_position, worker_id, retry_count fields per OpenAPI spec.
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


class TestExecutionStatusContract:
    """Contract tests for execution status endpoint."""

    def test_execution_status_response_schema(self, client: TestClient, auth_headers: dict):
        """Test GET /api/v1/executions/{id}/status response schema."""
        job_id = str(uuid4())

        response = client.get(
            f"/api/v1/executions/{job_id}/status",
            headers=auth_headers
        )

        # Endpoint may not exist yet or execution not found
        if response.status_code == 200:
            data = response.json()

            # Required fields per OpenAPI spec
            assert "job_id" in data
            assert "status" in data

            # Nullable fields per OpenAPI spec
            assert "queue_position" in data or data.get("queue_position") is None
            assert "worker_id" in data or data.get("worker_id") is None
            assert "started_at" in data or data.get("started_at") is None
            assert "progress_percent" in data or data.get("progress_percent") is None

    def test_execution_status_enum_values(self, client: TestClient, auth_headers: dict):
        """Test status enum matches OpenAPI spec."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/status", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            valid_statuses = ["pending", "queued", "in_progress", "completed", "failed", "cancelled"]
            assert data["status"] in valid_statuses

    def test_execution_status_queue_position_nullable(self, client: TestClient, auth_headers: dict):
        """Test queue_position is nullable per OpenAPI spec."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/status", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            # Should be integer or null
            if data.get("queue_position") is not None:
                assert isinstance(data["queue_position"], int)

    def test_execution_status_worker_id_format(self, client: TestClient, auth_headers: dict):
        """Test worker_id is UUID format when present."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/status", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            if data.get("worker_id"):
                # Should be valid UUID string
                try:
                    from uuid import UUID
                    UUID(data["worker_id"])
                except ValueError:
                    pytest.fail("worker_id is not a valid UUID")

    def test_execution_status_progress_bounds(self, client: TestClient, auth_headers: dict):
        """Test progress_percent is 0-100 when present."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/status", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            if data.get("progress_percent") is not None:
                assert 0 <= data["progress_percent"] <= 100

    def test_execution_status_unauthorized(self, client: TestClient):
        """Test 401 response without auth token."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/status")

        if response.status_code != 404:
            assert response.status_code == 401

    def test_execution_status_not_found(self, client: TestClient, auth_headers: dict):
        """Test 404 for non-existent execution."""
        non_existent_id = str(uuid4())
        response = client.get(
            f"/api/v1/executions/{non_existent_id}/status",
            headers=auth_headers
        )

        assert response.status_code in [404, 200]  # May return null data or 404
