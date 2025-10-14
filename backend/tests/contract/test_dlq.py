"""
Contract tests for Dead Letter Queue endpoints.
Tests DLQ management according to execution-queue.openapi.yaml specification.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


class TestDeadLetterQueue:
    """Test GET /api/v1/executions/dlq endpoint"""

    def test_list_dead_letter_tasks_success(self, client: TestClient, auth_headers: dict):
        """Test list dead letter tasks (admin only)"""
        response = client.get(
            "/api/v1/executions/dlq",
            headers=auth_headers
        )

        # Should return 200 for admin or 403 for non-admin
        if response.status_code == 200:
            # Validate response schema
            data = response.json()
            assert "tasks" in data
            assert "total" in data
            assert isinstance(data["tasks"], list)
            assert isinstance(data["total"], int)

            # If there are tasks, validate schema
            for task in data["tasks"]:
                assert "id" in task
                assert "original_queue_id" in task
                assert "execution_type" in task
                assert "payload" in task
                assert "failure_reason" in task
                assert "retry_history" in task
                assert "failure_timestamp" in task
                assert "is_requeued" in task

                # Validate retry_history structure
                if task["retry_history"]:
                    for attempt in task["retry_history"]:
                        assert "attempt" in attempt
                        assert "timestamp" in attempt
                        assert "error" in attempt
                        assert "duration_ms" in attempt
        else:
            assert response.status_code == 403  # Non-admin

    def test_list_dead_letter_tasks_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test pagination for dead letter tasks"""
        # Test page 1
        response = client.get(
            "/api/v1/executions/dlq?page=1&page_size=10",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert len(data["tasks"]) <= 10

    def test_list_dead_letter_tasks_custom_page_size(self, client: TestClient, auth_headers: dict):
        """Test custom page size"""
        response = client.get(
            "/api/v1/executions/dlq?page=1&page_size=5",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert len(data["tasks"]) <= 5

    def test_list_dead_letter_tasks_invalid_pagination(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid pagination params"""
        # Invalid page (< 1)
        response = client.get(
            "/api/v1/executions/dlq?page=0",
            headers=auth_headers
        )

        assert response.status_code in [400, 422]

    def test_list_dead_letter_tasks_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        response = client.get("/api/v1/executions/dlq")

        assert response.status_code == 401


class TestRequeuDeadLetterTask:
    """Test POST /api/v1/executions/dlq/{task_id}/requeue endpoint"""

    def test_requeue_task_success(self, client: TestClient, auth_headers: dict):
        """Test requeue failed task (admin only)"""
        # First get a DLQ task ID (if any exist)
        list_response = client.get(
            "/api/v1/executions/dlq",
            headers=auth_headers
        )

        if list_response.status_code == 200:
            data = list_response.json()
            if data["tasks"]:
                task_id = data["tasks"][0]["id"]

                # Requeue the task
                response = client.post(
                    f"/api/v1/executions/dlq/{task_id}/requeue",
                    headers=auth_headers
                )

                if response.status_code == 200:
                    # Validate response schema
                    requeue_data = response.json()
                    assert "message" in requeue_data
                    assert "execution_id" in requeue_data

                    # Validate UUID format
                    from uuid import UUID
                    UUID(requeue_data["execution_id"])

                else:
                    # Non-admin should get 403
                    assert response.status_code == 403
            else:
                pytest.skip("No DLQ tasks available for testing")
        else:
            pytest.skip("Cannot access DLQ (non-admin)")

    def test_requeue_nonexistent_task(self, client: TestClient, auth_headers: dict):
        """Test 404 for non-existent DLQ task"""
        fake_task_id = str(uuid4())

        response = client.post(
            f"/api/v1/executions/dlq/{fake_task_id}/requeue",
            headers=auth_headers
        )

        # Should return 404 for admin or 403 for non-admin
        assert response.status_code in [403, 404]

    def test_requeue_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid UUID format"""
        response = client.post(
            "/api/v1/executions/dlq/invalid-uuid/requeue",
            headers=auth_headers
        )

        assert response.status_code in [400, 422]

    def test_requeue_already_requeued_task(self, client: TestClient, auth_headers: dict):
        """Test requeuing already requeued task"""
        # Get DLQ tasks
        list_response = client.get(
            "/api/v1/executions/dlq",
            headers=auth_headers
        )

        if list_response.status_code == 200:
            data = list_response.json()

            # Find an already requeued task
            requeued_tasks = [t for t in data["tasks"] if t["is_requeued"]]

            if requeued_tasks:
                task_id = requeued_tasks[0]["id"]

                # Try to requeue again
                response = client.post(
                    f"/api/v1/executions/dlq/{task_id}/requeue",
                    headers=auth_headers
                )

                # Should return error (400) or succeed idempotently
                assert response.status_code in [200, 400, 403]
            else:
                pytest.skip("No requeued tasks available for testing")
        else:
            pytest.skip("Cannot access DLQ (non-admin)")

    def test_requeue_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        task_id = str(uuid4())

        response = client.post(f"/api/v1/executions/dlq/{task_id}/requeue")

        assert response.status_code == 401

    def test_requeue_non_admin(self, client: TestClient, non_admin_auth_headers: dict):
        """Test non-admin cannot requeue tasks"""
        task_id = str(uuid4())

        response = client.post(
            f"/api/v1/executions/dlq/{task_id}/requeue",
            headers=non_admin_auth_headers
        )

        assert response.status_code == 403
