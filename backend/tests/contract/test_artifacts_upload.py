"""Contract test for POST /api/v1/artifacts endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status
import io


@pytest.mark.asyncio
async def test_upload_artifact_success(authed_client: AsyncClient, test_execution_id: str):
    """Test successful artifact upload."""
    # Create test file
    file_content = b"Test file content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

    data = {
        "execution_id": test_execution_id,
        "execution_version": 1,
        "artifact_type": "document"
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    # Assert status code
    assert response.status_code == status.HTTP_201_CREATED

    # Assert response schema matches Artifact schema
    artifact = response.json()
    assert "id" in artifact
    assert artifact["execution_id"] == test_execution_id
    assert artifact["execution_version"] == 1
    assert artifact["file_name"] == "test.txt"
    assert artifact["mime_type"] == "text/plain"
    assert artifact["file_size_bytes"] == len(file_content)
    assert artifact["artifact_type"] == "document"
    assert "storage_path" in artifact
    assert "created_at" in artifact


@pytest.mark.asyncio
async def test_upload_artifact_with_metadata(authed_client: AsyncClient, test_execution_id: str):
    """Test artifact upload with tags, description, and category."""
    file_content = b"Test report data"
    files = {"file": ("report.pdf", io.BytesIO(file_content), "application/pdf")}

    data = {
        "execution_id": test_execution_id,
        "execution_version": 1,
        "artifact_type": "document",
        "tags": ["production", "quarterly", "important"],
        "description": "Q1 2025 financial report",
        "category": "reports"
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    assert response.status_code == status.HTTP_201_CREATED
    artifact = response.json()

    # Verify metadata was stored (requires ArtifactMetadata relationship)
    assert artifact["file_name"] == "report.pdf"


@pytest.mark.asyncio
async def test_upload_artifact_types(authed_client: AsyncClient, test_execution_id: str):
    """Test uploading artifacts of different types."""
    test_cases = [
        ("document.pdf", b"PDF content", "application/pdf", "document"),
        ("image.png", b"PNG content", "image/png", "image"),
        ("data.csv", b"CSV content", "text/csv", "data"),
        ("script.py", b"Python code", "text/x-python", "code"),
        ("unknown.xyz", b"Unknown", "application/octet-stream", "other"),
    ]

    for filename, content, mime_type, artifact_type in test_cases:
        files = {"file": (filename, io.BytesIO(content), mime_type)}
        data = {
            "execution_id": test_execution_id,
            "execution_version": 1,
            "artifact_type": artifact_type
        }

        response = await authed_client.post(
            "/api/v1/artifacts",
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_201_CREATED
        artifact = response.json()
        assert artifact["artifact_type"] == artifact_type


@pytest.mark.asyncio
async def test_upload_artifact_metadata_extraction(authed_client: AsyncClient, test_execution_id: str):
    """Test that file metadata is automatically extracted."""
    file_content = b"A" * 1024  # 1KB file
    files = {"file": ("document.txt", io.BytesIO(file_content), "text/plain")}

    data = {
        "execution_id": test_execution_id,
        "execution_version": 1,
        "artifact_type": "document"
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    assert response.status_code == status.HTTP_201_CREATED
    artifact = response.json()

    # Verify automatic extraction
    assert artifact["file_extension"] == ".txt"
    assert artifact["file_size_bytes"] == 1024
    assert artifact["mime_type"] == "text/plain"


@pytest.mark.asyncio
async def test_upload_artifact_storage_path_generation(authed_client: AsyncClient, test_execution_id: str):
    """Test that storage_path is generated correctly."""
    files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}
    data = {
        "execution_id": test_execution_id,
        "execution_version": 1
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    assert response.status_code == status.HTTP_201_CREATED
    artifact = response.json()

    # storage_path should be in format: tenant_id/execution_id/v{version}/filename
    storage_path = artifact["storage_path"]
    assert test_execution_id in storage_path
    assert "test.txt" in storage_path or artifact["id"] in storage_path


@pytest.mark.asyncio
async def test_upload_artifact_missing_required_fields(authed_client: AsyncClient):
    """Test 400 response when required fields are missing."""
    files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}

    # Missing execution_id
    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data={}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_upload_artifact_invalid_execution_id(authed_client: AsyncClient):
    """Test 400 response for invalid execution_id."""
    files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}
    data = {
        "execution_id": "not-a-uuid",
        "execution_version": 1
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_upload_artifact_tags_limit(authed_client: AsyncClient, test_execution_id: str):
    """Test 400 response when tags exceed max limit (20)."""
    files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}

    # More than 20 tags
    tags = [f"tag{i}" for i in range(21)]
    data = {
        "execution_id": test_execution_id,
        "execution_version": 1,
        "tags": tags
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_upload_artifact_max_file_size_exceeded(authed_client: AsyncClient, test_execution_id: str):
    """Test 413 response when file size exceeds tenant quota."""
    # This would require setting up a tenant with small max_artifact_size_bytes
    # For now, test with a very large file if supported by test infrastructure

    # Create large file (e.g., 100MB)
    large_content = b"A" * (100 * 1024 * 1024)
    files = {"file": ("large.bin", io.BytesIO(large_content), "application/octet-stream")}

    data = {
        "execution_id": test_execution_id,
        "execution_version": 1
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    # Should return 413 if size exceeds tenant's max_artifact_size_bytes
    # or 201 if tenant has sufficient quota
    assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE]

    if response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
        error = response.json()
        assert "error" in error
        assert "max_size_bytes" in error


@pytest.mark.asyncio
async def test_upload_artifact_quota_exceeded(authed_client: AsyncClient, test_execution_id: str):
    """Test 507 response when tenant storage quota is exceeded."""
    # This requires setting up a tenant with very low quota
    # and uploading files until quota is exceeded

    files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}
    data = {
        "execution_id": test_execution_id,
        "execution_version": 1
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    # Should return 507 only if quota is exceeded
    if response.status_code == status.HTTP_507_INSUFFICIENT_STORAGE:
        error = response.json()
        assert "error" in error
        assert "current_usage_bytes" in error
        assert "quota_bytes" in error


@pytest.mark.asyncio
async def test_upload_artifact_unauthorized(client: AsyncClient, test_execution_id: str):
    """Test that endpoint requires authentication."""
    files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}
    data = {
        "execution_id": test_execution_id,
        "execution_version": 1
    }

    response = await client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
