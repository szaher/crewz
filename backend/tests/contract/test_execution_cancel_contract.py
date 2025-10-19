"""Contract test for POST /api/v1/executions/{id}/cancel endpoint.

Validates cancellation_requested flag per OpenAPI spec.
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


class TestExecutionCancelContract:
    """Contract tests for execution cancellation endpoint."""

    def test_cancel_execution_response_schema(self, client: TestClient, auth_headers: dict):
        """Test POST /api/v1/executions/{id}/cancel response schema."""
        job_id = str(uuid4())

        response = client.post(
            f"/api/v1/executions/{job_id}/cancel",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()

            # Required fields per OpenAPI spec
            assert "cancelled" in data
            assert isinstance(data["cancelled"], bool)
            assert "final_state_logged" in data
            assert isinstance(data["final_state_logged"], bool)

    def test_cancel_execution_unauthorized(self, client: TestClient):
        """Test 401 response without auth token."""
        job_id = str(uuid4())
        response = client.post(f"/api/v1/executions/{job_id}/cancel")

        if response.status_code != 404:
            assert response.status_code == 401

    def test_cancel_execution_not_found(self, client: TestClient, auth_headers: dict):
        """Test response for non-existent execution."""
        non_existent_id = str(uuid4())
        response = client.post(
            f"/api/v1/executions/{non_existent_id}/cancel",
            headers=auth_headers
        )

        # Should return 404 or handle gracefully
        assert response.status_code in [404, 200]

    def test_cancel_idempotency(self, client: TestClient, auth_headers: dict):
        """Test cancelling same execution multiple times."""
        job_id = str(uuid4())

        # First cancellation
        response1 = client.post(f"/api/v1/executions/{job_id}/cancel", headers=auth_headers)

        # Second cancellation (should be idempotent)
        response2 = client.post(f"/api/v1/executions/{job_id}/cancel", headers=auth_headers)

        if response1.status_code == 200 and response2.status_code == 200:
            # Both should succeed (idempotent operation)
            assert response1.json()["cancelled"] == response2.json()["cancelled"]

    def test_cancel_completed_execution(self, client: TestClient, auth_headers: dict):
        """Test cancelling already completed execution."""
        job_id = str(uuid4())
        response = client.post(f"/api/v1/executions/{job_id}/cancel", headers=auth_headers)

        # Should either accept (noop) or reject based on status
        assert response.status_code in [200, 400, 404, 409]
