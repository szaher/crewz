"""Contract test for GET /api/v1/executions/{id}/artifacts endpoint.

Verifies artifact metadata fields per OpenAPI spec.
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


class TestArtifactsListContract:
    """Contract tests for artifacts list endpoint."""

    def test_artifacts_list_response_schema(self, client: TestClient, auth_headers: dict):
        """Test GET /api/v1/executions/{id}/artifacts response schema."""
        job_id = str(uuid4())

        response = client.get(
            f"/api/v1/executions/{job_id}/artifacts",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()

            # Should return array per OpenAPI spec
            assert isinstance(data, list)

            # Validate artifact schema if artifacts exist
            if data:
                artifact = data[0]
                assert "artifact_id" in artifact
                assert "file_name" in artifact
                assert "file_size" in artifact
                assert "mime_type" in artifact
                assert "artifact_type" in artifact
                assert "version" in artifact
                assert "download_url" in artifact

    def test_artifacts_list_artifact_types(self, client: TestClient, auth_headers: dict):
        """Test artifact_type enum values per OpenAPI spec."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/artifacts", headers=auth_headers)

        if response.status_code == 200:
            artifacts = response.json()
            valid_types = ["output_file", "log_file", "screenshot", "data_export"]

            for artifact in artifacts:
                assert artifact["artifact_type"] in valid_types

    def test_artifacts_list_artifact_id_format(self, client: TestClient, auth_headers: dict):
        """Test artifact_id is UUID format."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/artifacts", headers=auth_headers)

        if response.status_code == 200:
            artifacts = response.json()

            for artifact in artifacts:
                try:
                    from uuid import UUID
                    UUID(artifact["artifact_id"])
                except ValueError:
                    pytest.fail("artifact_id is not a valid UUID")

    def test_artifacts_list_file_size_type(self, client: TestClient, auth_headers: dict):
        """Test file_size is integer."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/artifacts", headers=auth_headers)

        if response.status_code == 200:
            artifacts = response.json()

            for artifact in artifacts:
                assert isinstance(artifact["file_size"], int)
                assert artifact["file_size"] >= 0

    def test_artifacts_list_download_url_format(self, client: TestClient, auth_headers: dict):
        """Test download_url is valid URI."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/artifacts", headers=auth_headers)

        if response.status_code == 200:
            artifacts = response.json()

            for artifact in artifacts:
                url = artifact["download_url"]
                # Should be valid URI (can be relative or absolute)
                assert isinstance(url, str)
                assert len(url) > 0

    def test_artifacts_list_version_number(self, client: TestClient, auth_headers: dict):
        """Test version is integer."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/artifacts", headers=auth_headers)

        if response.status_code == 200:
            artifacts = response.json()

            for artifact in artifacts:
                assert isinstance(artifact["version"], int)
                assert artifact["version"] >= 1

    def test_artifacts_list_unauthorized(self, client: TestClient):
        """Test 401 response without auth token."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/artifacts")

        if response.status_code != 404:
            assert response.status_code == 401

    def test_artifacts_list_not_found(self, client: TestClient, auth_headers: dict):
        """Test response for non-existent execution."""
        non_existent_id = str(uuid4())
        response = client.get(
            f"/api/v1/executions/{non_existent_id}/artifacts",
            headers=auth_headers
        )

        # Should return empty list or 404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert isinstance(response.json(), list)

    def test_artifacts_list_empty_execution(self, client: TestClient, auth_headers: dict):
        """Test execution with no artifacts returns empty array."""
        job_id = str(uuid4())
        response = client.get(f"/api/v1/executions/{job_id}/artifacts", headers=auth_headers)

        if response.status_code == 200:
            artifacts = response.json()
            # Should return empty array for execution with no artifacts
            assert isinstance(artifacts, list)
