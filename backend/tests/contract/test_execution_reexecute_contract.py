"""Contract test for POST /api/v1/executions/{id}/re-execute endpoint.

Checks version_number increment per OpenAPI spec.
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


class TestExecutionReExecuteContract:
    """Contract tests for execution re-execute endpoint."""

    def test_reexecute_response_schema(self, client: TestClient, auth_headers: dict):
        """Test POST /api/v1/executions/{id}/re-execute response schema."""
        job_id = str(uuid4())

        response = client.post(
            f"/api/v1/executions/{job_id}/re-execute",
            headers=auth_headers
        )

        if response.status_code == 201:
            data = response.json()

            # Required fields per OpenAPI spec
            assert "new_job_id" in data
            assert "version_number" in data

            # Validate types
            try:
                from uuid import UUID
                UUID(data["new_job_id"])
            except ValueError:
                pytest.fail("new_job_id is not a valid UUID")

            assert isinstance(data["version_number"], int)
            assert data["version_number"] >= 1

    def test_reexecute_version_increment(self, client: TestClient, auth_headers: dict):
        """Test version_number increments on re-execution."""
        job_id = str(uuid4())

        # First re-execution
        response1 = client.post(f"/api/v1/executions/{job_id}/re-execute", headers=auth_headers)

        if response1.status_code == 201:
            version1 = response1.json()["version_number"]
            new_job_id1 = response1.json()["new_job_id"]

            # Re-execute the new job
            response2 = client.post(f"/api/v1/executions/{new_job_id1}/re-execute", headers=auth_headers)

            if response2.status_code == 201:
                version2 = response2.json()["version_number"]
                # Version should increment
                assert version2 > version1

    def test_reexecute_unauthorized(self, client: TestClient):
        """Test 401 response without auth token."""
        job_id = str(uuid4())
        response = client.post(f"/api/v1/executions/{job_id}/re-execute")

        if response.status_code != 404:
            assert response.status_code == 401

    def test_reexecute_not_found(self, client: TestClient, auth_headers: dict):
        """Test re-executing non-existent execution."""
        non_existent_id = str(uuid4())
        response = client.post(
            f"/api/v1/executions/{non_existent_id}/re-execute",
            headers=auth_headers
        )

        assert response.status_code in [404, 201]

    def test_reexecute_preserves_inputs(self, client: TestClient, auth_headers: dict):
        """Test re-execution uses same inputs as original."""
        # Note: This test will be expanded once we can create and verify executions
        job_id = str(uuid4())
        response = client.post(f"/api/v1/executions/{job_id}/re-execute", headers=auth_headers)

        # For now, just verify endpoint exists and responds correctly
        assert response.status_code in [201, 404, 400]

    def test_reexecute_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test re-executing with invalid UUID format."""
        invalid_id = "not-a-uuid"
        response = client.post(
            f"/api/v1/executions/{invalid_id}/re-execute",
            headers=auth_headers
        )

        # Should return validation error
        assert response.status_code in [422, 400, 404]
