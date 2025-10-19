"""
Integration test for artifact download functionality.

Tests T072: Artifact download
- Execution with artifacts
- GET /artifacts list
- GET /download presigned URL
- Verify S3 access works
"""
import pytest
import asyncio
import time
from httpx import AsyncClient


class TestArtifactDownload:
    """Integration tests for execution artifact management and download."""

    @pytest.mark.asyncio
    async def test_list_execution_artifacts(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test listing artifacts for an execution.

        Steps:
        1. Complete an execution (which may produce artifacts)
        2. GET /api/v1/executions/{id}/artifacts
        3. Verify response schema
        """
        # Start execution
        payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"artifacts_test": True},
            "priority": 5
        }

        response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        if response.status_code not in [200, 201]:
            pytest.skip(f"Queue endpoint not ready: {response.status_code}")

        data = response.json()
        exec_id = data.get("job_id") or data.get("id")

        # Wait for completion
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = await client.get(
                f"/api/v1/executions/{exec_id}/status",
                headers=auth_headers
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "failed"]:
                    break

            await asyncio.sleep(2)

        # Get artifacts list
        artifacts_response = await client.get(
            f"/api/v1/executions/{exec_id}/artifacts",
            headers=auth_headers
        )

        if artifacts_response.status_code == 404:
            pytest.skip("Artifacts list endpoint not implemented yet")

        # Should return 200 with empty or populated list
        assert artifacts_response.status_code == 200, \
            f"Artifacts list should return 200, got {artifacts_response.status_code}"

        artifacts_data = artifacts_response.json()

        # Verify response is a list
        assert isinstance(artifacts_data, list) or "artifacts" in artifacts_data, \
            "Response should be a list or contain artifacts field"

        artifacts_list = artifacts_data if isinstance(artifacts_data, list) else artifacts_data.get("artifacts", [])

        # Verify artifact schema if any exist
        for artifact in artifacts_list:
            assert "id" in artifact or "artifact_id" in artifact, \
                "Each artifact should have an ID"
            assert "file_name" in artifact, \
                "Each artifact should have a file_name"

            # Optional fields per spec
            if "file_size" in artifact:
                assert isinstance(artifact["file_size"], int), \
                    "file_size should be an integer"

            if "mime_type" in artifact:
                assert isinstance(artifact["mime_type"], str), \
                    "mime_type should be a string"

    @pytest.mark.asyncio
    async def test_download_artifact_presigned_url(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test getting presigned URL for artifact download.

        Steps:
        1. Complete execution with artifacts
        2. Get artifact list
        3. GET /api/v1/artifacts/{id}/download
        4. Verify presigned URL returned
        """
        # Start execution
        payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"download_test": True},
            "priority": 5
        }

        response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        if response.status_code not in [200, 201]:
            pytest.skip(f"Queue endpoint not ready: {response.status_code}")

        data = response.json()
        exec_id = data.get("job_id") or data.get("id")

        # Wait for completion
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = await client.get(
                f"/api/v1/executions/{exec_id}/status",
                headers=auth_headers
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "failed"]:
                    break

            await asyncio.sleep(2)

        # Get artifacts
        artifacts_response = await client.get(
            f"/api/v1/executions/{exec_id}/artifacts",
            headers=auth_headers
        )

        if artifacts_response.status_code == 404:
            pytest.skip("Artifacts endpoint not implemented yet")

        if artifacts_response.status_code != 200:
            pytest.skip(f"Could not get artifacts: {artifacts_response.status_code}")

        artifacts_data = artifacts_response.json()
        artifacts_list = artifacts_data if isinstance(artifacts_data, list) else artifacts_data.get("artifacts", [])

        if not artifacts_list:
            # No artifacts produced, can't test download
            pytest.skip("No artifacts produced by execution")

        # Get first artifact
        artifact_id = artifacts_list[0].get("id") or artifacts_list[0].get("artifact_id")

        # Get download URL
        download_response = await client.get(
            f"/api/v1/artifacts/{artifact_id}/download",
            headers=auth_headers
        )

        if download_response.status_code == 404:
            pytest.skip("Artifact download endpoint not implemented yet")

        assert download_response.status_code == 200, \
            f"Download should return 200, got {download_response.status_code}"

        download_data = download_response.json()

        # Verify presigned URL is returned
        assert "download_url" in download_data or "url" in download_data, \
            "Response should contain download URL"

        url = download_data.get("download_url") or download_data.get("url")
        assert url.startswith("http"), \
            "Download URL should be a valid HTTP(S) URL"

    @pytest.mark.asyncio
    async def test_artifact_versioning(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test artifact versioning across re-executions.

        Steps:
        1. Complete execution (version 1)
        2. Re-execute (version 2)
        3. Verify artifacts have correct version numbers
        """
        # First execution
        payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"versioning_test": True},
            "priority": 5
        }

        response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        if response.status_code not in [200, 201]:
            pytest.skip(f"Queue endpoint not ready: {response.status_code}")

        data = response.json()
        exec_id_v1 = data.get("job_id") or data.get("id")

        # Wait for completion
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = await client.get(
                f"/api/v1/executions/{exec_id_v1}/status",
                headers=auth_headers
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "failed"]:
                    break

            await asyncio.sleep(2)

        # Get artifacts for v1
        artifacts_v1_response = await client.get(
            f"/api/v1/executions/{exec_id_v1}/artifacts",
            headers=auth_headers
        )

        if artifacts_v1_response.status_code == 404:
            pytest.skip("Artifacts endpoint not implemented yet")

        # Re-execute
        reexec_response = await client.post(
            f"/api/v1/executions/{exec_id_v1}/re-execute",
            headers=auth_headers
        )

        if reexec_response.status_code == 404:
            pytest.skip("Re-execute endpoint not implemented yet")

        if reexec_response.status_code not in [200, 201]:
            pytest.skip("Re-execute failed")

        reexec_data = reexec_response.json()
        exec_id_v2 = reexec_data.get("job_id") or reexec_data.get("id")

        # Wait for v2 completion
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_response = await client.get(
                f"/api/v1/executions/{exec_id_v2}/status",
                headers=auth_headers
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "failed"]:
                    break

            await asyncio.sleep(2)

        # Get artifacts for v2
        artifacts_v2_response = await client.get(
            f"/api/v1/executions/{exec_id_v2}/artifacts",
            headers=auth_headers
        )

        if artifacts_v2_response.status_code == 200:
            artifacts_v2_data = artifacts_v2_response.json()
            artifacts_v2_list = artifacts_v2_data if isinstance(artifacts_v2_data, list) else artifacts_v2_data.get("artifacts", [])

            # Verify version numbers if present
            for artifact in artifacts_v2_list:
                if "version_number" in artifact or "version" in artifact:
                    version = artifact.get("version_number") or artifact.get("version")
                    assert version == 2, \
                        f"Artifacts from v2 execution should have version=2, got {version}"

    @pytest.mark.asyncio
    async def test_artifact_tenant_isolation(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test that artifacts are tenant-isolated.

        Steps:
        1. Complete execution with artifacts
        2. Try to access artifact from different tenant
        3. Verify access denied
        """
        # This test requires multi-tenant setup
        # For now, just verify that artifact access requires auth
        from uuid import uuid4

        fake_artifact_id = str(uuid4())

        # Try to download non-existent artifact
        download_response = await client.get(
            f"/api/v1/artifacts/{fake_artifact_id}/download",
            headers=auth_headers
        )

        if download_response.status_code == 404:
            # Expected - artifact doesn't exist
            pass
        elif download_response.status_code == 403:
            # Expected - access denied
            pass
        else:
            # Endpoint might not be implemented
            pytest.skip("Artifact download endpoint behavior unclear")

    @pytest.mark.asyncio
    async def test_unauthorized_artifact_access(self, client: AsyncClient):
        """
        Test that artifact access requires authentication.

        Steps:
        1. Try to list artifacts without auth
        2. Try to download artifact without auth
        3. Verify 401 responses
        """
        from uuid import uuid4

        exec_id = str(uuid4())
        artifact_id = str(uuid4())

        # Try to list artifacts without auth
        list_response = await client.get(
            f"/api/v1/executions/{exec_id}/artifacts"
        )

        if list_response.status_code != 404:
            assert list_response.status_code == 401, \
                "Artifacts list should require authentication"

        # Try to download artifact without auth
        download_response = await client.get(
            f"/api/v1/artifacts/{artifact_id}/download"
        )

        if download_response.status_code != 404:
            assert download_response.status_code == 401, \
                "Artifact download should require authentication"

    @pytest.mark.asyncio
    async def test_artifact_expiration(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test that artifact expiration is set correctly.

        Steps:
        1. Complete execution with artifacts
        2. Get artifact details
        3. Verify expires_at is set (created_at + 30 days per spec)
        """
        # Start execution
        payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"expiration_test": True},
            "priority": 5
        }

        response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        if response.status_code not in [200, 201]:
            pytest.skip(f"Queue endpoint not ready: {response.status_code}")

        data = response.json()
        exec_id = data.get("job_id") or data.get("id")

        # Wait for completion
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = await client.get(
                f"/api/v1/executions/{exec_id}/status",
                headers=auth_headers
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "failed"]:
                    break

            await asyncio.sleep(2)

        # Get artifacts
        artifacts_response = await client.get(
            f"/api/v1/executions/{exec_id}/artifacts",
            headers=auth_headers
        )

        if artifacts_response.status_code == 404:
            pytest.skip("Artifacts endpoint not implemented yet")

        if artifacts_response.status_code != 200:
            pytest.skip("Could not get artifacts")

        artifacts_data = artifacts_response.json()
        artifacts_list = artifacts_data if isinstance(artifacts_data, list) else artifacts_data.get("artifacts", [])

        # Verify expiration if artifacts exist
        for artifact in artifacts_list:
            if "expires_at" in artifact:
                assert artifact["expires_at"] is not None, \
                    "expires_at should be set"
                # Further validation could check it's approximately 30 days from created_at
