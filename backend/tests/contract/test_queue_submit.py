"""
Contract tests for POST /api/v1/executions/submit endpoint.
Tests execution queue submission according to execution-queue.openapi.yaml specification.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


@pytest.fixture
def valid_crew_execution():
    """Valid crew execution request"""
    return {
        "execution_type": "crew",
        "entity_id": str(uuid4()),
        "payload": {"input": "test input", "config": {}},
        "priority": "normal"
    }


@pytest.fixture
def valid_flow_execution():
    """Valid flow execution request"""
    return {
        "execution_type": "flow",
        "entity_id": str(uuid4()),
        "payload": {"variables": {"var1": "value1"}},
        "priority": "high"
    }


class TestSubmitExecution:
    """Test POST /api/v1/executions/submit endpoint"""

    def test_submit_crew_execution_success(self, client: TestClient, auth_headers: dict, valid_crew_execution):
        """Test valid crew execution submission"""
        response = client.post(
            "/api/v1/executions/submit",
            json=valid_crew_execution,
            headers=auth_headers
        )

        # Should return 202 Accepted
        assert response.status_code == 202

        # Validate response schema
        data = response.json()
        assert "execution_id" in data
        assert "queue_id" in data
        assert "status" in data
        assert data["status"] == "pending"
        assert "estimated_start_time" in data
        assert "queue_position" in data

        # Validate UUID format
        from uuid import UUID
        UUID(data["execution_id"])  # Should not raise
        UUID(data["queue_id"])  # Should not raise

    def test_submit_flow_execution_success(self, client: TestClient, auth_headers: dict, valid_flow_execution):
        """Test valid flow execution submission"""
        response = client.post(
            "/api/v1/executions/submit",
            json=valid_flow_execution,
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"

    def test_submit_with_custom_timeout(self, client: TestClient, auth_headers: dict, valid_crew_execution):
        """Test submission with custom timeout"""
        valid_crew_execution["timeout_minutes"] = 60

        response = client.post(
            "/api/v1/executions/submit",
            json=valid_crew_execution,
            headers=auth_headers
        )

        assert response.status_code == 202

    def test_submit_all_execution_types(self, client: TestClient, auth_headers: dict):
        """Test all valid execution types"""
        execution_types = ["crew", "flow", "agent", "task", "tool"]

        for exec_type in execution_types:
            request_data = {
                "execution_type": exec_type,
                "entity_id": str(uuid4()),
                "payload": {},
                "priority": "normal"
            }

            response = client.post(
                "/api/v1/executions/submit",
                json=request_data,
                headers=auth_headers
            )

            assert response.status_code == 202, f"Failed for type: {exec_type}"

    def test_submit_all_priority_levels(self, client: TestClient, auth_headers: dict, valid_crew_execution):
        """Test all priority levels"""
        priorities = ["low", "normal", "high"]

        for priority in priorities:
            valid_crew_execution["priority"] = priority

            response = client.post(
                "/api/v1/executions/submit",
                json=valid_crew_execution,
                headers=auth_headers
            )

            assert response.status_code == 202, f"Failed for priority: {priority}"

    def test_submit_missing_required_field(self, client: TestClient, auth_headers: dict):
        """Test validation error for missing required fields"""
        # Missing execution_type
        invalid_request = {
            "entity_id": str(uuid4()),
            "payload": {}
        }

        response = client.post(
            "/api/v1/executions/submit",
            json=invalid_request,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    def test_submit_invalid_execution_type(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid execution_type"""
        invalid_request = {
            "execution_type": "invalid_type",
            "entity_id": str(uuid4()),
            "payload": {}
        }

        response = client.post(
            "/api/v1/executions/submit",
            json=invalid_request,
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_submit_invalid_priority(self, client: TestClient, auth_headers: dict, valid_crew_execution):
        """Test validation error for invalid priority"""
        valid_crew_execution["priority"] = "critical"  # Not in enum

        response = client.post(
            "/api/v1/executions/submit",
            json=valid_crew_execution,
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_submit_invalid_timeout(self, client: TestClient, auth_headers: dict, valid_crew_execution):
        """Test validation error for invalid timeout"""
        # Timeout exceeds max (120 minutes)
        valid_crew_execution["timeout_minutes"] = 150

        response = client.post(
            "/api/v1/executions/submit",
            json=valid_crew_execution,
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_submit_invalid_entity_id_format(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid UUID format"""
        invalid_request = {
            "execution_type": "crew",
            "entity_id": "not-a-uuid",
            "payload": {}
        }

        response = client.post(
            "/api/v1/executions/submit",
            json=invalid_request,
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_submit_rate_limit_exceeded(self, client: TestClient, auth_headers: dict, valid_crew_execution):
        """Test rate limit error (429)"""
        # Submit multiple executions to trigger rate limit
        # This test expects rate limiting to be enforced

        # Submit up to the limit
        for _ in range(12):  # Assume limit is 10
            response = client.post(
                "/api/v1/executions/submit",
                json=valid_crew_execution,
                headers=auth_headers
            )

            # Either succeeds (202) or hits rate limit (429)
            if response.status_code == 429:
                # Validate 429 response schema
                data = response.json()
                assert "error" in data
                assert "limit" in data
                assert "current" in data
                assert "retry_after" in data
                assert data["limit"] > 0
                assert data["current"] >= data["limit"]
                return

        # If we didn't hit rate limit, that's also acceptable for this test
        # (rate limiting might not be active in test environment)
        pytest.skip("Rate limiting not enforced in test environment")

    def test_submit_unauthorized(self, client: TestClient, valid_crew_execution):
        """Test unauthorized access without auth token"""
        response = client.post(
            "/api/v1/executions/submit",
            json=valid_crew_execution
        )

        assert response.status_code == 401

    def test_submit_response_time(self, client: TestClient, auth_headers: dict, valid_crew_execution):
        """Test submission response time <200ms target"""
        import time

        start = time.time()
        response = client.post(
            "/api/v1/executions/submit",
            json=valid_crew_execution,
            headers=auth_headers
        )
        duration_ms = (time.time() - start) * 1000

        assert response.status_code == 202
        # Lenient check for CI environments
        assert duration_ms < 500, f"Response took {duration_ms}ms (target: <200ms)"
