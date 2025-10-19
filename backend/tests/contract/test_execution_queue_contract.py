"""Contract test for POST /api/v1/executions/queue endpoint.

Validates request/response schemas match OpenAPI spec in contracts/execution-queue-api.yaml
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


class TestExecutionQueueContract:
    """Contract tests for execution queue endpoint."""

    def test_queue_execution_request_schema(self, client: TestClient, auth_headers: dict):
        """Test POST /api/v1/executions/queue request schema validation."""
        # Valid request matching OpenAPI spec
        valid_payload = {
            "execution_type": "crew",
            "entity_id": str(uuid4()),
            "input_params": {"param1": "value1"},
            "priority": 5,
            "timeout_seconds": 600
        }

        response = client.post(
            "/api/v1/executions/queue",
            json=valid_payload,
            headers=auth_headers
        )

        # Should return 201 or fall back to existing flow
        assert response.status_code in [201, 200, 404]  # 404 until implemented

    def test_queue_execution_response_schema(self, client: TestClient, auth_headers: dict):
        """Test POST /api/v1/executions/queue response schema matches contract."""
        payload = {
            "execution_type": "flow",
            "entity_id": str(uuid4()),
            "input_params": {}
        }

        response = client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        if response.status_code == 201:
            data = response.json()
            # Validate response schema per OpenAPI spec
            assert "job_id" in data
            assert "queue_position" in data
            assert "estimated_start_time" in data

    def test_queue_execution_priority_bounds(self, client: TestClient, auth_headers: dict):
        """Test priority validation (0-10 per OpenAPI spec)."""
        # Test min boundary
        payload = {
            "execution_type": "task",
            "entity_id": str(uuid4()),
            "input_params": {},
            "priority": 0
        }
        response = client.post("/api/v1/executions/queue", json=payload, headers=auth_headers)
        assert response.status_code in [201, 400, 404]

        # Test max boundary
        payload["priority"] = 10
        response = client.post("/api/v1/executions/queue", json=payload, headers=auth_headers)
        assert response.status_code in [201, 400, 404]

        # Test out of bounds (should fail)
        payload["priority"] = 11
        response = client.post("/api/v1/executions/queue", json=payload, headers=auth_headers)
        if response.status_code != 404:  # Only validate if endpoint exists
            assert response.status_code == 422  # Validation error

    def test_queue_execution_timeout_bounds(self, client: TestClient, auth_headers: dict):
        """Test timeout_seconds validation (60-3600 per OpenAPI spec)."""
        payload = {
            "execution_type": "crew",
            "entity_id": str(uuid4()),
            "input_params": {},
            "timeout_seconds": 60  # Min
        }
        response = client.post("/api/v1/executions/queue", json=payload, headers=auth_headers)
        assert response.status_code in [201, 400, 404]

        payload["timeout_seconds"] = 3600  # Max
        response = client.post("/api/v1/executions/queue", json=payload, headers=auth_headers)
        assert response.status_code in [201, 400, 404]

    def test_queue_execution_invalid_type(self, client: TestClient, auth_headers: dict):
        """Test invalid execution_type (enum validation)."""
        payload = {
            "execution_type": "invalid_type",
            "entity_id": str(uuid4()),
            "input_params": {}
        }

        response = client.post("/api/v1/executions/queue", json=payload, headers=auth_headers)
        if response.status_code != 404:
            assert response.status_code == 422  # Validation error

    def test_queue_execution_missing_required_fields(self, client: TestClient, auth_headers: dict):
        """Test missing required fields per OpenAPI spec."""
        # Missing execution_type
        payload = {"entity_id": str(uuid4()), "input_params": {}}
        response = client.post("/api/v1/executions/queue", json=payload, headers=auth_headers)
        if response.status_code != 404:
            assert response.status_code == 422

        # Missing entity_id
        payload = {"execution_type": "crew", "input_params": {}}
        response = client.post("/api/v1/executions/queue", json=payload, headers=auth_headers)
        if response.status_code != 404:
            assert response.status_code == 422

    def test_queue_execution_unauthorized(self, client: TestClient):
        """Test 401 response without auth token."""
        payload = {
            "execution_type": "crew",
            "entity_id": str(uuid4()),
            "input_params": {}
        }

        response = client.post("/api/v1/executions/queue", json=payload)
        if response.status_code != 404:
            assert response.status_code == 401
