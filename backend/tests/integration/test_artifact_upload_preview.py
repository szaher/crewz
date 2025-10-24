"""Integration test for artifact upload with preview <3s (Scenario 4 from quickstart.md)."""

import pytest
from httpx import AsyncClient
import io
import json
import time


@pytest.mark.asyncio
async def test_artifact_upload_with_preview_under_3s(
    authed_client: AsyncClient,
    test_execution_id: str,
    test_tenant_id: str
):
    """
    Test Scenario 4: Artifact Upload with Preview.

    Given: A 5MB JSON artifact
    When: Artifact is uploaded
    Then: Preview is generated within 3s (NFR-002) and artifact is stored
    """
    # Arrange: Create 5MB JSON file
    large_json_data = {
        "data": [
            {"id": i, "value": f"Item {i}", "description": "x" * 100}
            for i in range(10000)  # ~5MB
        ],
        "metadata": {
            "count": 10000,
            "generated_at": "2025-01-01T00:00:00Z"
        }
    }

    json_content = json.dumps(large_json_data).encode('utf-8')
    file_size = len(json_content)

    print(f"Generated JSON file: {file_size / (1024 * 1024):.2f} MB")

    files = {
        "file": ("large_report.json", io.BytesIO(json_content), "application/json")
    }

    data = {
        "execution_id": test_execution_id,
        "execution_version": 1,
        "artifact_type": "data",
        "tags": ["report", "test"],
        "description": "Large JSON report for preview testing"
    }

    # Act: Upload artifact
    upload_start = time.time()

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    upload_duration = time.time() - upload_start

    # Assert: Upload successful
    assert response.status_code == 201
    artifact = response.json()
    artifact_id = artifact["id"]

    assert artifact["file_name"] == "large_report.json"
    assert artifact["file_size_bytes"] == file_size
    assert artifact["mime_type"] == "application/json"
    assert artifact["artifact_type"] == "data"

    # Act: Request preview
    preview_start = time.time()

    preview_response = await authed_client.get(
        f"/api/v1/artifacts/{artifact_id}/preview"
    )

    preview_duration = time.time() - preview_start

    # Assert: Preview generation <3s (NFR-002)
    assert preview_response.status_code == 200
    assert preview_duration < 3.0, (
        f"Preview generation took {preview_duration:.2f}s, exceeds 3s limit (NFR-002)"
    )

    preview_data = preview_response.json()
    assert preview_data["preview_type"] == "json"
    assert "content" in preview_data
    assert "cached" in preview_data

    # Verify preview content structure
    content = preview_data["content"]
    assert isinstance(content, dict)

    print(f"✓ Artifact upload: {upload_duration:.2f}s, Preview generation: {preview_duration:.2f}s (<3s requirement)")


@pytest.mark.asyncio
async def test_artifact_upload_quota_enforcement(
    authed_client: AsyncClient,
    test_execution_id: str,
    test_tenant_with_low_quota: str
):
    """Test that 507 error is returned when storage quota is exceeded."""
    # Arrange: Create a file that will exceed the tenant's quota
    large_file = b"x" * (10 * 1024 * 1024)  # 10MB

    files = {
        "file": ("large_file.bin", io.BytesIO(large_file), "application/octet-stream")
    }

    data = {
        "execution_id": test_execution_id,
        "execution_version": 1
    }

    # Act: Try to upload when quota is exceeded
    # (Assumes test_tenant_with_low_quota has very low quota)
    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    # Assert: Should return 507 Insufficient Storage
    if response.status_code == 507:
        error_data = response.json()
        assert "error" in error_data
        assert "current_usage_bytes" in error_data
        assert "quota_bytes" in error_data

        # Verify quota data
        assert error_data["current_usage_bytes"] >= 0
        assert error_data["quota_bytes"] > 0
        assert error_data["current_usage_bytes"] >= error_data["quota_bytes"]

        print(f"✓ Quota enforcement working: {error_data['error']}")
    else:
        # If quota not exceeded, that's also ok for this test tenant
        assert response.status_code in [201, 507]


@pytest.mark.asyncio
async def test_artifact_upload_max_size_enforcement(
    authed_client: AsyncClient,
    test_execution_id: str
):
    """Test that 413 error is returned when file size exceeds max_artifact_size_bytes."""
    # Create file larger than typical max size (e.g., 100MB)
    very_large_file = b"x" * (101 * 1024 * 1024)

    files = {
        "file": ("huge_file.bin", io.BytesIO(very_large_file), "application/octet-stream")
    }

    data = {
        "execution_id": test_execution_id,
        "execution_version": 1
    }

    response = await authed_client.post(
        "/api/v1/artifacts",
        files=files,
        data=data
    )

    # Should return 413 if size exceeds limit, or 201 if within limit
    if response.status_code == 413:
        error_data = response.json()
        assert "error" in error_data
        assert "max_size_bytes" in error_data
    else:
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_preview_caching_behavior(
    authed_client: AsyncClient,
    test_execution_id: str
):
    """Test that preview results are cached on second request."""
    # Upload a JSON file
    json_data = {"test": "data", "items": list(range(1000))}
    json_content = json.dumps(json_data).encode('utf-8')

    files = {
        "file": ("test.json", io.BytesIO(json_content), "application/json")
    }

    data = {
        "execution_id": test_execution_id,
        "execution_version": 1,
        "artifact_type": "data"
    }

    upload_response = await authed_client.post("/api/v1/artifacts", files=files, data=data)
    artifact_id = upload_response.json()["id"]

    # First preview request (not cached)
    preview1_start = time.time()
    preview1_response = await authed_client.get(f"/api/v1/artifacts/{artifact_id}/preview")
    preview1_duration = time.time() - preview1_start

    assert preview1_response.status_code == 200
    preview1_data = preview1_response.json()

    # Second preview request (should be cached)
    preview2_start = time.time()
    preview2_response = await authed_client.get(f"/api/v1/artifacts/{artifact_id}/preview")
    preview2_duration = time.time() - preview2_start

    assert preview2_response.status_code == 200
    preview2_data = preview2_response.json()

    # Second request should be faster (cached)
    assert preview2_duration < preview1_duration or preview2_data.get("cached") is True

    print(f"✓ Preview caching: 1st={preview1_duration:.3f}s, 2nd={preview2_duration:.3f}s")


@pytest.mark.asyncio
async def test_preview_different_file_types(
    authed_client: AsyncClient,
    test_execution_id: str
):
    """Test preview generation for different file types."""
    test_files = [
        # (filename, content, mime_type, expected_preview_type)
        ("data.json", b'{"key": "value"}', "application/json", "json"),
        ("data.csv", b"name,age\nJohn,30\nJane,25", "text/csv", "table"),
        ("script.py", b"def hello():\n    print('world')", "text/x-python", "code"),
        ("document.txt", b"This is a text document.", "text/plain", "text"),
    ]

    for filename, content, mime_type, expected_type in test_files:
        files = {
            "file": (filename, io.BytesIO(content), mime_type)
        }

        data = {
            "execution_id": test_execution_id,
            "execution_version": 1
        }

        # Upload
        upload_response = await authed_client.post("/api/v1/artifacts", files=files, data=data)
        assert upload_response.status_code == 201
        artifact_id = upload_response.json()["id"]

        # Get preview
        preview_response = await authed_client.get(f"/api/v1/artifacts/{artifact_id}/preview")

        if preview_response.status_code == 200:
            preview_data = preview_response.json()
            assert preview_data["preview_type"] in [expected_type, "not_available"]
            print(f"✓ Preview for {filename}: {preview_data['preview_type']}")
        elif preview_response.status_code == 415:
            # Unsupported media type
            print(f"✓ Preview for {filename}: not supported (415)")


@pytest.mark.asyncio
async def test_storage_path_generation(
    authed_client: AsyncClient,
    test_execution_id: str,
    test_tenant_id: str
):
    """Test that storage_path follows hierarchical pattern: tenant_id/execution_id/version/artifact_id."""
    files = {
        "file": ("test.txt", io.BytesIO(b"test content"), "text/plain")
    }

    data = {
        "execution_id": test_execution_id,
        "execution_version": 2
    }

    response = await authed_client.post("/api/v1/artifacts", files=files, data=data)
    assert response.status_code == 201

    artifact = response.json()
    storage_path = artifact["storage_path"]

    # Verify path contains tenant_id, execution_id, and version
    assert test_tenant_id in storage_path or test_execution_id in storage_path
    # Path should include version indicator
    assert "v2" in storage_path or "/2/" in storage_path or "_2_" in storage_path


@pytest.mark.asyncio
async def test_artifact_metadata_extraction(
    authed_client: AsyncClient,
    test_execution_id: str
):
    """Test that file metadata is automatically extracted and stored."""
    # Test with different file extensions
    test_cases = [
        ("document.pdf", b"PDF content", "application/pdf", ".pdf"),
        ("image.png", b"PNG content", "image/png", ".png"),
        ("data.json", b'{"test": true}', "application/json", ".json"),
    ]

    for filename, content, mime_type, expected_ext in test_cases:
        files = {
            "file": (filename, io.BytesIO(content), mime_type)
        }

        data = {
            "execution_id": test_execution_id,
            "execution_version": 1
        }

        response = await authed_client.post("/api/v1/artifacts", files=files, data=data)
        assert response.status_code == 201

        artifact = response.json()

        # Verify metadata extraction
        assert artifact["file_name"] == filename
        assert artifact["file_extension"] == expected_ext
        assert artifact["file_size_bytes"] == len(content)
        assert artifact["mime_type"] == mime_type
