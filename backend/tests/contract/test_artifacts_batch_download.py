"""Contract test for POST /api/v1/artifacts/batch/download endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime
from uuid import uuid4


@pytest.mark.asyncio
async def test_batch_download_artifacts_success(authed_client: AsyncClient, test_artifact_ids: list):
    """Test successful batch download of multiple artifacts."""
    payload = {
        "artifact_ids": test_artifact_ids[:5],  # Download 5 artifacts
        "include_metadata": True
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema per artifacts-api.yaml
    data = response.json()
    assert "download_url" in data
    assert "expires_at" in data
    assert "total_size_bytes" in data
    assert "artifact_count" in data

    # Validate types
    assert isinstance(data["download_url"], str)
    assert data["download_url"].startswith("http")
    assert isinstance(data["total_size_bytes"], int)
    assert data["artifact_count"] == 5

    # Validate expires_at is a valid timestamp in the future
    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    assert expires_at > datetime.utcnow()


@pytest.mark.asyncio
async def test_batch_download_with_metadata_inclusion(authed_client: AsyncClient, test_artifact_ids: list):
    """Test batch download with metadata.json included."""
    payload = {
        "artifact_ids": test_artifact_ids[:3],
        "include_metadata": True
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # When include_metadata=true, ZIP should contain metadata.json
    # This would need to be verified by downloading and inspecting the ZIP
    # For contract test, just verify the parameter is accepted
    assert "download_url" in data


@pytest.mark.asyncio
async def test_batch_download_without_metadata(authed_client: AsyncClient, test_artifact_ids: list):
    """Test batch download without metadata.json."""
    payload = {
        "artifact_ids": test_artifact_ids[:3],
        "include_metadata": False
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_batch_download_single_artifact(authed_client: AsyncClient, test_artifact_ids: list):
    """Test batch download with single artifact (edge case)."""
    payload = {
        "artifact_ids": [test_artifact_ids[0]]
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["artifact_count"] == 1


@pytest.mark.asyncio
async def test_batch_download_max_artifacts(authed_client: AsyncClient, test_artifact_ids: list):
    """Test batch download with maximum allowed artifacts (100)."""
    # Create list of 100 artifact IDs
    artifact_ids = test_artifact_ids[:100] if len(test_artifact_ids) >= 100 else test_artifact_ids

    payload = {
        "artifact_ids": artifact_ids
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    # Should succeed if <= 100 artifacts
    if len(artifact_ids) <= 100:
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["artifact_count"] == len(artifact_ids)


@pytest.mark.asyncio
async def test_batch_download_exceeds_max_limit(authed_client: AsyncClient):
    """Test 400 response when artifact count exceeds max (100)."""
    # Create list of 101 artifact IDs
    artifact_ids = [str(uuid4()) for _ in range(101)]

    payload = {
        "artifact_ids": artifact_ids
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    error = response.json()
    assert "error" in error


@pytest.mark.asyncio
async def test_batch_download_empty_list(authed_client: AsyncClient):
    """Test 400 response when artifact_ids is empty."""
    payload = {
        "artifact_ids": []
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_batch_download_missing_artifact_ids(authed_client: AsyncClient):
    """Test 400 response when artifact_ids is missing."""
    payload = {
        "include_metadata": True
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_batch_download_invalid_uuid_format(authed_client: AsyncClient):
    """Test 400 response when artifact_ids contains invalid UUIDs."""
    payload = {
        "artifact_ids": ["not-a-uuid", "also-invalid"]
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_batch_download_non_existent_artifacts(authed_client: AsyncClient):
    """Test handling of non-existent artifact IDs."""
    non_existent_ids = [str(uuid4()), str(uuid4())]

    payload = {
        "artifact_ids": non_existent_ids
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    # Could return 404 or 200 with empty ZIP (depends on spec)
    # For now, expect 400 or 404
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
async def test_batch_download_mixed_valid_invalid(authed_client: AsyncClient, test_artifact_ids: list):
    """Test batch download with mix of valid and invalid artifact IDs."""
    mixed_ids = test_artifact_ids[:2] + [str(uuid4()), str(uuid4())]

    payload = {
        "artifact_ids": mixed_ids
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    # Should handle partial success or fail entirely (depends on spec)
    # For contract test, just verify response is valid
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND
    ]


@pytest.mark.asyncio
async def test_batch_download_soft_deleted_artifacts(authed_client: AsyncClient, test_artifact_deleted_ids: list):
    """Test that soft-deleted artifacts are excluded from batch download."""
    payload = {
        "artifact_ids": test_artifact_deleted_ids
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    # Should return 404 or exclude deleted artifacts
    assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]


@pytest.mark.asyncio
async def test_batch_download_total_size_calculation(authed_client: AsyncClient, test_artifact_ids: list):
    """Test that total_size_bytes is correctly calculated."""
    payload = {
        "artifact_ids": test_artifact_ids[:3]
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # total_size_bytes should be > 0 for valid artifacts
    assert data["total_size_bytes"] > 0


@pytest.mark.asyncio
async def test_batch_download_presigned_url_expiration(authed_client: AsyncClient, test_artifact_ids: list):
    """Test that pre-signed URL has reasonable expiration time."""
    payload = {
        "artifact_ids": test_artifact_ids[:2]
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    now = datetime.utcnow()

    # URL should expire within 1 hour (default per storage.py config)
    time_diff = (expires_at - now).total_seconds()
    assert 0 < time_diff <= 3600  # 1 hour in seconds


@pytest.mark.asyncio
async def test_batch_download_unauthorized(client: AsyncClient, test_artifact_ids: list):
    """Test that endpoint requires authentication."""
    payload = {
        "artifact_ids": test_artifact_ids[:3]
    }

    response = await client.post("/api/v1/artifacts/batch/download", json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_batch_download_tenant_isolation(authed_client: AsyncClient, other_tenant_artifact_ids: list):
    """Test that artifacts from other tenants cannot be batch downloaded."""
    payload = {
        "artifact_ids": other_tenant_artifact_ids
    }

    response = await authed_client.post("/api/v1/artifacts/batch/download", json=payload)

    # Should return 404 or 403 for other tenant's artifacts
    assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]
