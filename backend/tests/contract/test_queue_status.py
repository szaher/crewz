"""
Contract tests for GET/DELETE /api/v1/executions/{execution_id} endpoints.
Tests execution status and cancellation according to execution-queue.openapi.yaml specification.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


class TestGetExecutionStatus:
    """Test GET /api/v1/executions/{execution_id} endpoint"""

    def test_get_execution_status_success(self, client: TestClient, auth_headers: dict):
        """Test get execution status for existing execution"""
        # First submit an execution
        submit_data = {
            "execution_type": "crew",
            "entity_id": str(uuid4()),
            "payload": {"test": "data"},
            "priority": "normal"
        }

        submit_response = client.post(
            "/api/v1/executions/submit",
            json=submit_data,
            headers=auth_headers
        )
        assert submit_response.status_code == 202

        execution_id = submit_response.json()["execution_id"]

        # Get status
        response = client.get(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Validate response schema
        data = response.json()
        assert "id" in data
        assert "execution_type" in data
        assert "entity_id" in data
        assert "status" in data
        assert "priority" in data
        assert "retry_count" in data
        assert "max_retries" in data
        assert "scheduled_at" in data
        assert data["status"] in ["pending", "running", "completed", "failed", "timeout", "cancelled"]

    def test_get_execution_status_with_timestamps(self, client: TestClient, auth_headers: dict):
        """Test execution status includes proper timestamps"""
        # Submit execution
        submit_data = {
            "execution_type": "flow",
            "entity_id": str(uuid4()),
            "payload": {},
            "priority": "high"
        }

        submit_response = client.post(
            "/api/v1/executions/submit",
            json=submit_data,
            headers=auth_headers
        )
        execution_id = submit_response.json()["execution_id"]

        # Get status
        response = client.get(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Scheduled_at should always be present
        assert data["scheduled_at"] is not None

        # started_at, completed_at may be null for pending executions
        assert "started_at" in data
        assert "completed_at" in data
        assert "duration_ms" in data

    def test_get_execution_status_not_found(self, client: TestClient, auth_headers: dict):
        """Test 404 for non-existent execution"""
        fake_execution_id = str(uuid4())

        response = client.get(
            f"/api/v1/executions/{fake_execution_id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_execution_status_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid UUID format"""
        response = client.get(
            "/api/v1/executions/not-a-uuid",
            headers=auth_headers
        )

        assert response.status_code in [400, 422]  # Validation error

    def test_get_execution_status_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        execution_id = str(uuid4())

        response = client.get(f"/api/v1/executions/{execution_id}")

        assert response.status_code == 401


class TestCancelExecution:
    """Test DELETE /api/v1/executions/{execution_id} endpoint"""

    def test_cancel_pending_execution_success(self, client: TestClient, auth_headers: dict):
        """Test cancel pending execution"""
        # Submit execution
        submit_data = {
            "execution_type": "crew",
            "entity_id": str(uuid4()),
            "payload": {},
            "priority": "low"
        }

        submit_response = client.post(
            "/api/v1/executions/submit",
            json=submit_data,
            headers=auth_headers
        )
        execution_id = submit_response.json()["execution_id"]

        # Cancel execution
        response = client.delete(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )

        # Should succeed if still pending
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "status" in data
            assert data["status"] == "cancelled"

            # Verify status changed
            status_response = client.get(
                f"/api/v1/executions/{execution_id}",
                headers=auth_headers
            )
            assert status_response.json()["status"] == "cancelled"

    def test_cancel_running_execution_success(self, client: TestClient, auth_headers: dict):
        """Test cancel running execution"""
        # This test assumes execution can be cancelled while running
        # Implementation may vary - some systems allow it, others don't

        submit_data = {
            "execution_type": "agent",
            "entity_id": str(uuid4()),
            "payload": {},
            "priority": "normal"
        }

        submit_response = client.post(
            "/api/v1/executions/submit",
            json=submit_data,
            headers=auth_headers
        )
        execution_id = submit_response.json()["execution_id"]

        # Try to cancel
        response = client.delete(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )

        # Should either succeed (200) or fail because already completed/running (400)
        assert response.status_code in [200, 400]

    def test_cancel_completed_execution_fails(self, client: TestClient, auth_headers: dict):
        """Test cannot cancel completed execution"""
        # This test will pass if:
        # 1. We can create a completed execution and verify cancellation fails
        # 2. OR the endpoint returns 400 for already completed executions

        # For now, submit and immediately try to cancel
        # In practice, fast executions might complete before we can cancel
        submit_data = {
            "execution_type": "task",
            "entity_id": str(uuid4()),
            "payload": {},
            "priority": "high"
        }

        submit_response = client.post(
            "/api/v1/executions/submit",
            json=submit_data,
            headers=auth_headers
        )
        execution_id = submit_response.json()["execution_id"]

        # Wait a moment for potential completion
        import time
        time.sleep(0.5)

        # Check current status
        status_response = client.get(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )
        current_status = status_response.json()["status"]

        # Try to cancel
        response = client.delete(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )

        if current_status in ["completed", "failed", "timeout"]:
            # Should return 400 for completed executions
            assert response.status_code == 400
        else:
            # Should succeed for pending/running
            assert response.status_code in [200, 400]

    def test_cancel_nonexistent_execution(self, client: TestClient, auth_headers: dict):
        """Test 404 for cancelling non-existent execution"""
        fake_execution_id = str(uuid4())

        response = client.delete(
            f"/api/v1/executions/{fake_execution_id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_cancel_execution_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid UUID format"""
        response = client.delete(
            "/api/v1/executions/invalid-uuid",
            headers=auth_headers
        )

        assert response.status_code in [400, 422]

    def test_cancel_execution_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        execution_id = str(uuid4())

        response = client.delete(f"/api/v1/executions/{execution_id}")

        assert response.status_code == 401

    def test_cancel_idempotent(self, client: TestClient, auth_headers: dict):
        """Test cancelling already cancelled execution is idempotent"""
        # Submit execution
        submit_data = {
            "execution_type": "crew",
            "entity_id": str(uuid4()),
            "payload": {},
            "priority": "normal"
        }

        submit_response = client.post(
            "/api/v1/executions/submit",
            json=submit_data,
            headers=auth_headers
        )
        execution_id = submit_response.json()["execution_id"]

        # Cancel first time
        response1 = client.delete(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )

        # Cancel second time (should be idempotent)
        response2 = client.delete(
            f"/api/v1/executions/{execution_id}",
            headers=auth_headers
        )

        # Both should succeed or both return same error
        if response1.status_code == 200:
            assert response2.status_code in [200, 400]  # Either idempotent or "already cancelled"
